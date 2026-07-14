import os
import io
import base64
import html
import random
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import streamlit as st

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None

try:
    import psycopg2
except Exception:
    psycopg2 = None

try:
    import barcode
    from barcode.writer import ImageWriter
    BARCODE_DISPONIBLE = True
except Exception:
    BARCODE_DISPONIBLE = False


ARCHIVO_INVENTARIO = "inventario_kits.csv"
ARCHIVO_HISTORIAL = "historial_kits.csv"
ARCHIVO_CATALOGO_TIPOS = "catalogo_tipos_por_ensayo.csv"
ARCHIVO_ENSAYOS = "ensayos_configurados.csv"

BASE_DIR = Path(__file__).resolve().parent
ARCHIVO_INVENTARIO = str(BASE_DIR / ARCHIVO_INVENTARIO)
ARCHIVO_HISTORIAL = str(BASE_DIR / ARCHIVO_HISTORIAL)
ARCHIVO_CATALOGO_TIPOS = str(BASE_DIR / ARCHIVO_CATALOGO_TIPOS)
ARCHIVO_ENSAYOS = str(BASE_DIR / ARCHIVO_ENSAYOS)

TABLA_INVENTARIO = "inventario_kits"
TABLA_HISTORIAL = "historial_kits"
TABLA_CATALOGO_TIPOS = "catalogo_tipos_por_ensayo"
TABLA_ENSAYOS = "ensayos_configurados"

DB_TABLAS = {
    ARCHIVO_INVENTARIO: {
        "tabla": TABLA_INVENTARIO,
        "columnas_ui": ["Codigo de barras", "Ensayo", "Tipo de kit", "Caducidad"],
        "columnas_db": ["codigo_barras", "ensayo", "tipo_de_kit", "caducidad"],
    },
    ARCHIVO_HISTORIAL: {
        "tabla": TABLA_HISTORIAL,
        "columnas_ui": [
            "Fecha",
            "Hora",
            "Accion",
            "Codigo de barras",
            "Ensayo",
            "Tipo de kit",
            "Caducidad",
            "Detalle",
        ],
        "columnas_db": [
            "fecha",
            "hora",
            "accion",
            "codigo_barras",
            "ensayo",
            "tipo_de_kit",
            "caducidad",
            "detalle",
        ],
    },
    ARCHIVO_CATALOGO_TIPOS: {
        "tabla": TABLA_CATALOGO_TIPOS,
        "columnas_ui": ["Ensayo", "Tipo de kit"],
        "columnas_db": ["ensayo", "tipo_de_kit"],
    },
    ARCHIVO_ENSAYOS: {
        "tabla": TABLA_ENSAYOS,
        "columnas_ui": ["Ensayo"],
        "columnas_db": ["ensayo"],
    },
}

SECRETS_CANDIDATES = [
    BASE_DIR / ".streamlit" / "secrets.toml",
    BASE_DIR / "agenda-streamlit" / ".streamlit" / "secrets.toml",
]


def _leer_toml(path: Path) -> dict:
    if tomllib is None or not path.exists():
        return {}
    try:
        with path.open("rb") as archivo:
            return tomllib.load(archivo)
    except Exception:
        return {}


def obtener_database_url() -> str:
    env_url = (os.getenv("DATABASE_URL") or "").strip()
    if env_url:
        return env_url

    try:
        secret_url = str(st.secrets.get("DATABASE_URL", "")).strip()
        if secret_url:
            return secret_url
    except Exception:
        pass

    for secrets_path in SECRETS_CANDIDATES:
        data = _leer_toml(secrets_path)
        url = str(data.get("DATABASE_URL") or "").strip()
        if url:
            return url

    return ""


DATABASE_URL = obtener_database_url()


def _usar_postgres() -> bool:
    return bool(DATABASE_URL and psycopg2 is not None)


def _conexion_postgres():
    if not _usar_postgres():
        return None
    return psycopg2.connect(DATABASE_URL, connect_timeout=10)


def _asegurar_esquema_postgres() -> None:
    if not _usar_postgres():
        return

    ddl = [
        f"""
        CREATE TABLE IF NOT EXISTS {TABLA_INVENTARIO} (
            id BIGSERIAL PRIMARY KEY,
            codigo_barras TEXT NOT NULL UNIQUE,
            ensayo TEXT NOT NULL,
            tipo_de_kit TEXT NOT NULL,
            caducidad TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {TABLA_HISTORIAL} (
            id BIGSERIAL PRIMARY KEY,
            fecha TEXT NOT NULL,
            hora TEXT NOT NULL,
            accion TEXT NOT NULL,
            codigo_barras TEXT NOT NULL,
            ensayo TEXT NOT NULL,
            tipo_de_kit TEXT NOT NULL,
            caducidad TEXT,
            detalle TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {TABLA_CATALOGO_TIPOS} (
            id BIGSERIAL PRIMARY KEY,
            ensayo TEXT NOT NULL,
            tipo_de_kit TEXT NOT NULL,
            UNIQUE (ensayo, tipo_de_kit)
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {TABLA_ENSAYOS} (
            id BIGSERIAL PRIMARY KEY,
            ensayo TEXT NOT NULL UNIQUE
        )
        """,
    ]

    with _conexion_postgres() as conn:
        with conn.cursor() as cur:
            for sentencia in ddl:
                cur.execute(sentencia)


def _normalizar_para_sql(valor) -> str:
    if valor is None:
        return ""
    if pd.isna(valor):
        return ""
    return str(valor)


def _leer_tabla_postgres(path: str, columnas_ui: list[str]) -> pd.DataFrame:
    config = DB_TABLAS.get(path)
    if not config or not _usar_postgres():
        return pd.DataFrame(columns=columnas_ui)

    try:
        with _conexion_postgres() as conn:
            consulta = f"SELECT {', '.join(config['columnas_db'])} FROM {config['tabla']} ORDER BY id"
            df = pd.read_sql_query(consulta, conn)
    except Exception:
        return pd.DataFrame(columns=columnas_ui)

    if df.empty:
        return pd.DataFrame(columns=columnas_ui)

    df = df.rename(columns=dict(zip(config["columnas_db"], config["columnas_ui"])))
    for col in columnas_ui:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].fillna("").astype(str)
    return df[columnas_ui].copy()


def _reemplazar_tabla_postgres(path: str, df: pd.DataFrame, columnas_ui: list[str]) -> bool:
    config = DB_TABLAS.get(path)
    if not config or not _usar_postgres():
        return False

    try:
        with _conexion_postgres() as conn:
            with conn.cursor() as cur:
                cur.execute(f"TRUNCATE TABLE {config['tabla']}")
                if df.empty:
                    return True

                filas = []
                for _, fila in df[columnas_ui].iterrows():
                    filas.append(tuple(_normalizar_para_sql(fila[col]).strip() for col in columnas_ui))

                marcadores = ", ".join(["%s"] * len(config["columnas_db"]))
                columnas_sql = ", ".join(config["columnas_db"])
                cur.executemany(
                    f"INSERT INTO {config['tabla']} ({columnas_sql}) VALUES ({marcadores})",
                    filas,
                )
        return True
    except Exception:
        return False


def _insertar_fila_postgres(path: str, datos: dict) -> bool:
    config = DB_TABLAS.get(path)
    if not config or not _usar_postgres():
        return False

    try:
        with _conexion_postgres() as conn:
            with conn.cursor() as cur:
                columnas_sql = ", ".join(config["columnas_db"])
                marcadores = ", ".join(["%s"] * len(config["columnas_db"]))
                valores = [datos.get(col, "") for col in config["columnas_ui"]]
                cur.execute(
                    f"INSERT INTO {config['tabla']} ({columnas_sql}) VALUES ({marcadores}) ON CONFLICT DO NOTHING",
                    valores,
                )
        return True
    except Exception:
        return False


try:
    _asegurar_esquema_postgres()
except Exception as exc:
    if DATABASE_URL:
        st.warning(f"No se pudo inicializar PostgreSQL para el inventario: {exc}")

COLUMNAS_INVENTARIO = ["Codigo de barras", "Ensayo", "Tipo de kit", "Caducidad"]
COLUMNAS_HISTORIAL = [
    "Fecha",
    "Hora",
    "Accion",
    "Codigo de barras",
    "Ensayo",
    "Tipo de kit",
    "Caducidad",
    "Detalle",
]
COLUMNAS_CATALOGO = ["Ensayo", "Tipo de kit"]
COLUMNAS_ENSAYOS = ["Ensayo"]

DIAS_AVISO_CADUCIDAD = 30

ENSAYOS_CONFIGURADOS = [
    "2245",
    "2256",
    "2246",
    "2274",
    "2257",
    "MONUMMENTAL-6",
    "MAJESTEC-3",
    "CAEL 101-302",
    "CAEL 101-301",
    "DREAMM-8",
    "DREAMM-10",
    "DREAMM-15",
    "BGB",
    "WAVE",
    "NURIX 1",
    "NURIX 2",
    "NURIX 3",
    "ENTRUST",
    "ALANIS",
    "PERSEUS",
]


def cargar_tabla(path: str, columnas: list[str]) -> pd.DataFrame:
    if _usar_postgres() and path in DB_TABLAS:
        return _leer_tabla_postgres(path, columnas)

    if os.path.exists(path):
        try:
            df = pd.read_csv(path, dtype=str)
        except Exception:
            df = pd.DataFrame(columns=columnas)
    else:
        df = pd.DataFrame(columns=columnas)

    for col in columnas:
        if col not in df.columns:
            df[col] = ""

    for col in columnas:
        df[col] = df[col].fillna("").astype(str)

    return df[columnas].copy()


def guardar_tabla(path: str, df: pd.DataFrame, columnas: list[str]) -> None:
    if _usar_postgres() and path in DB_TABLAS:
        _reemplazar_tabla_postgres(path, df, columnas)
        return

    out = df.copy()
    for col in columnas:
        if col not in out.columns:
            out[col] = ""
        out[col] = out[col].fillna("").astype(str)
    out[columnas].to_csv(path, index=False)


def cargar_inventario() -> pd.DataFrame:
    return cargar_tabla(ARCHIVO_INVENTARIO, COLUMNAS_INVENTARIO)


def guardar_inventario(df: pd.DataFrame) -> None:
    guardar_tabla(ARCHIVO_INVENTARIO, df, COLUMNAS_INVENTARIO)


def cargar_historial() -> pd.DataFrame:
    return cargar_tabla(ARCHIVO_HISTORIAL, COLUMNAS_HISTORIAL)


def guardar_historial(df: pd.DataFrame) -> None:
    guardar_tabla(ARCHIVO_HISTORIAL, df, COLUMNAS_HISTORIAL)


def cargar_catalogo_tipos() -> pd.DataFrame:
    df = cargar_tabla(ARCHIVO_CATALOGO_TIPOS, COLUMNAS_CATALOGO)
    df["Ensayo"] = df["Ensayo"].str.strip()
    df["Tipo de kit"] = df["Tipo de kit"].str.strip()
    df = df[(df["Ensayo"] != "") & (df["Tipo de kit"] != "")].drop_duplicates().reset_index(drop=True)
    return df


def cargar_ensayos_configurados() -> list[str]:
    df = cargar_tabla(ARCHIVO_ENSAYOS, COLUMNAS_ENSAYOS)
    ensayos = (
        df["Ensayo"].fillna("").astype(str).str.strip().replace("", pd.NA).dropna().tolist()
    )
    return sorted(set(ensayos), key=str.lower)


def guardar_ensayos_configurados(ensayos: list[str]) -> None:
    limpios = [str(e).strip() for e in ensayos if str(e).strip()]
    unicos = sorted(set(limpios), key=str.lower)
    df = pd.DataFrame({"Ensayo": unicos})
    guardar_tabla(ARCHIVO_ENSAYOS, df, COLUMNAS_ENSAYOS)


def agregar_ensayo_configurado(ensayo: str) -> bool:
    nuevo = str(ensayo).strip()
    if not nuevo:
        return False

    actuales = cargar_ensayos_configurados()
    if nuevo in actuales:
        return False

    if _usar_postgres() and _insertar_fila_postgres(ARCHIVO_ENSAYOS, {"Ensayo": nuevo}):
        return True

    guardar_ensayos_configurados(actuales + [nuevo])
    return True


def guardar_catalogo_tipos(df: pd.DataFrame) -> None:
    out = df.copy()
    out["Ensayo"] = out["Ensayo"].fillna("").astype(str).str.strip()
    out["Tipo de kit"] = out["Tipo de kit"].fillna("").astype(str).str.strip()
    out = out[(out["Ensayo"] != "") & (out["Tipo de kit"] != "")].drop_duplicates().reset_index(drop=True)
    guardar_tabla(ARCHIVO_CATALOGO_TIPOS, out, COLUMNAS_CATALOGO)


def registrar_tipo_ensayo(ensayo: str, tipo_kit: str) -> None:
    ensayo = str(ensayo).strip()
    tipo_kit = str(tipo_kit).strip()
    if not ensayo or not tipo_kit:
        return

    if _usar_postgres() and _insertar_fila_postgres(
        ARCHIVO_CATALOGO_TIPOS,
        {"Ensayo": ensayo, "Tipo de kit": tipo_kit},
    ):
        return

    catalogo = cargar_catalogo_tipos()
    existe = ((catalogo["Ensayo"] == ensayo) & (catalogo["Tipo de kit"] == tipo_kit)).any()
    if not existe:
        nuevo = pd.DataFrame([{"Ensayo": ensayo, "Tipo de kit": tipo_kit}])
        guardar_catalogo_tipos(pd.concat([catalogo, nuevo], ignore_index=True))


def obtener_tipos_por_ensayo(ensayo: str) -> list[str]:
    catalogo = cargar_catalogo_tipos()
    tipos = catalogo[catalogo["Ensayo"] == str(ensayo).strip()]["Tipo de kit"].tolist()
    return sorted(set(tipos), key=str.lower)


def sincronizar_catalogo_desde_inventario(df_inventario: pd.DataFrame) -> None:
    base = cargar_catalogo_tipos()
    desde_inv = df_inventario[["Ensayo", "Tipo de kit"]].copy()
    guardar_catalogo_tipos(pd.concat([base, desde_inv], ignore_index=True))


def normalizar_codigo(codigo: str) -> str:
    if not isinstance(codigo, str):
        return ""
    return codigo.strip().upper()


def generar_codigo_automatico(ensayo: str, tipo_kit: str, caducidad: str) -> str:
    """Genera un numero aleatorio unico de 10 digitos."""
    return str(random.randint(1000000000, 9999999999))


def generar_codigo_automatico_unico(ensayo: str, tipo_kit: str, caducidad: str, codigos_existentes: set[str]) -> str:
    """Genera un numero aleatorio de 10 digitos que no existe en el inventario."""
    while True:
        codigo = generar_codigo_automatico(ensayo, tipo_kit, caducidad)
        if codigo not in codigos_existentes:
            return codigo


def generar_barcode_png_bytes(codigo: str):
    if not BARCODE_DISPONIBLE:
        return None

    code128 = barcode.get_barcode_class("code128")
    obj = code128(str(codigo), writer=ImageWriter())
    buffer = io.BytesIO()
    obj.write(
        buffer,
        options={
            "module_width": 0.28,
            "module_height": 10,
            "quiet_zone": 1,
            "write_text": False,
            "font_size": 0,
            "text_distance": 0,
        },
    )
    return buffer.getvalue()


def construir_html_pegatinas(df_sel: pd.DataFrame) -> str:
    etiquetas = []
    for _, row in df_sel.iterrows():
        codigo = str(row["Codigo de barras"])
        ensayo = str(row["Ensayo"])
        tipo = str(row["Tipo de kit"])
        cad = str(row["Caducidad"])

        img_bytes = generar_barcode_png_bytes(codigo)
        if img_bytes:
            img_b64 = base64.b64encode(img_bytes).decode("ascii")
            img_tag = f'<img src="data:image/png;base64,{img_b64}" alt="{html.escape(codigo)}" />'
        else:
            img_tag = '<div class="no-img">No disponible</div>'

        etiquetas.append(
            f"""
            <div class="etiqueta">
                <div class="ensayo">{html.escape(ensayo)}</div>
                <div class="tipo">{html.escape(tipo)}</div>
                <div class="cad">Caducidad: {html.escape(cad if cad else 'N/A')}</div>
                <div class="barcode">{img_tag}</div>
                <div class="codigo">{html.escape(codigo)}</div>
            </div>
            """
        )

    por_hoja = 24  # A4: 3 columnas x 8 filas
    paginas = []
    for i in range(0, len(etiquetas), por_hoja):
        bloque = etiquetas[i : i + por_hoja]
        faltan = por_hoja - len(bloque)
        if faltan > 0:
            bloque.extend(['<div class="etiqueta etiqueta-vacia"></div>'] * faltan)
        paginas.append(f'<div class="grid">{"".join(bloque)}</div>')

    contenido = "\n".join(paginas)
    return f"""
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <title>Pegatinas de kits</title>
  <style>
        @page {{ size: A4 portrait; margin: 0; }}
    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; padding: 0; }}
    body {{ font-family: Arial, sans-serif; }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(3, 70mm);
            grid-template-rows: repeat(8, 37.125mm);
            gap: 0;
            width: 210mm;
            height: 297mm;
            page-break-after: always;
            break-after: page;
        }}
        .grid:last-child {{
            page-break-after: auto;
            break-after: auto;
        }}
                .etiqueta {{ padding: 1mm; min-height: 0; display: flex; flex-direction: column; gap: 0.1mm; overflow: hidden; }}
                .etiqueta-vacia {{ visibility: hidden; }}
        .ensayo {{ font-weight: 700; font-size: 8pt; line-height: 1.1; text-align: center; }}
                .tipo {{ font-size: 7pt; line-height: 1.1; text-align: center; }}
                .cad {{ font-size: 6.5pt; line-height: 1.1; text-align: center; margin-bottom: 0.2mm; }}
                .barcode {{ margin-top: 0; min-height: 9.5mm; display: flex; align-items: flex-end; justify-content: center; }}
                .codigo {{ font-size: 6.5pt; text-align: center; line-height: 1.05; letter-spacing: 0.2px; }}
                    img {{ width: 100%; height: auto; max-height: 9.5mm; object-fit: contain; display: block; margin: 0 auto; }}
                    .no-img {{ height: 9.5mm; width: 100%; display: grid; place-items: center; border: 1px dashed #999; font-size: 7pt; }}
  </style>
</head>
<body>
    {contenido}
</body>
</html>
"""


def parsear_fecha(cadena: str):
    if not isinstance(cadena, str):
        return None
    valor = cadena.strip()
    if not valor:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(valor, fmt).date()
        except ValueError:
            continue
    return None


def formatear_fecha(fecha_date: date | None) -> str:
    if fecha_date is None:
        return ""
    return fecha_date.strftime("%d/%m/%Y")


def registrar_movimiento(accion: str, codigo: str, ensayo: str, tipo_kit: str, caducidad: str, detalle: str = "") -> None:
    ahora = datetime.now()
    fila = {
        "Fecha": ahora.strftime("%d/%m/%Y"),
        "Hora": ahora.strftime("%H:%M:%S"),
        "Accion": accion,
        "Codigo de barras": codigo,
        "Ensayo": ensayo,
        "Tipo de kit": tipo_kit,
        "Caducidad": caducidad,
        "Detalle": detalle,
    }

    if _usar_postgres() and _insertar_fila_postgres(ARCHIVO_HISTORIAL, fila):
        return

    hist = cargar_historial()
    hist = pd.concat([hist, pd.DataFrame([fila])], ignore_index=True)
    guardar_historial(hist)


def calcular_alertas(df: pd.DataFrame):
    hoy = date.today()
    caducados = []
    proximos = []

    for _, fila in df.iterrows():
        codigo = str(fila.get("Codigo de barras", ""))
        ensayo = str(fila.get("Ensayo", ""))
        tipo = str(fila.get("Tipo de kit", ""))
        cad = str(fila.get("Caducidad", ""))

        f_cad = parsear_fecha(cad)
        if not f_cad:
            continue

        if f_cad < hoy:
            caducados.append((codigo, ensayo, tipo, cad))
        else:
            dias_rest = (f_cad - hoy).days
            if dias_rest <= DIAS_AVISO_CADUCIDAD:
                proximos.append((codigo, ensayo, tipo, cad, dias_rest))

    return caducados, proximos


def ensayos_disponibles(df: pd.DataFrame) -> list[str]:
    configurados_extra = cargar_ensayos_configurados()
    presentes = sorted(
        df["Ensayo"].fillna("").astype(str).str.strip().replace("", pd.NA).dropna().unique().tolist()
    )
    base = ENSAYOS_CONFIGURADOS + [e for e in configurados_extra if e not in ENSAYOS_CONFIGURADOS]
    todos = base + [e for e in presentes if e not in base]
    return todos


st.set_page_config(page_title="Inventario de Kits", page_icon="🧪", layout="wide")
st.title("🧪 Inventario de Cajas de Kits")
st.write(
    "Escaneas una caja para darla de alta con su ensayo, tipo y caducidad. "
    "Cuando se usa, la vuelves a escanear y se elimina del inventario activo."
)

inventario = cargar_inventario()
sincronizar_catalogo_desde_inventario(inventario)

caducados, proximos = calcular_alertas(inventario)

with st.expander("Alertas", expanded=True):
    if caducados:
        st.error("Cajas caducadas:")
        for codigo, ensayo, tipo, cad in caducados:
            st.write(f"- {codigo} | {ensayo} | {tipo} | Caducidad: {cad}")
    else:
        st.success("No hay cajas caducadas.")

    if proximos:
        st.warning(f"Cajas proximas a caducar (<= {DIAS_AVISO_CADUCIDAD} dias):")
        for codigo, ensayo, tipo, cad, dias in proximos:
            st.write(f"- {codigo} | {ensayo} | {tipo} | Caduca: {cad} (en {dias} dias)")
    else:
        st.info("No hay cajas proximas a caducar.")

st.markdown("---")
st.subheader("Inventarios por ensayo")

with st.form("form_nuevo_ensayo", clear_on_submit=True):
    nuevo_ensayo = st.text_input(
        "Añadir ensayo nuevo",
        placeholder="Escribe nombre o codigo del ensayo",
    )
    guardar_ensayo = st.form_submit_button("Guardar ensayo")

    if guardar_ensayo:
        ensayo_limpio = str(nuevo_ensayo).strip()
        if not ensayo_limpio:
            st.error("Escribe un nombre de ensayo valido.")
        elif ensayo_limpio in ensayos_disponibles(inventario):
            st.warning("Ese ensayo ya existe.")
        else:
            agregado = agregar_ensayo_configurado(ensayo_limpio)
            if agregado:
                st.success(f"Ensayo añadido: {ensayo_limpio}")
                st.rerun()
            else:
                st.warning("No se pudo añadir el ensayo.")

lista_ensayos = ensayos_disponibles(inventario)
tabs = st.tabs(lista_ensayos)
historial_global = cargar_historial()

for i, ensayo_tab in enumerate(lista_ensayos):
    with tabs[i]:
        data_ensayo = inventario[inventario["Ensayo"].astype(str).str.strip() == ensayo_tab].copy()
        st.caption(f"Ensayo: {ensayo_tab} | Cajas activas: {len(data_ensayo)}")

        st.markdown("**Alta por escaneo**")
        with st.form(f"form_alta_{i}", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                codigo_escaneado = st.text_input(
                    "Codigo de barras",
                    placeholder="Escanea aqui con la pistola",
                    key=f"codigo_alta_{i}",
                )
            with col2:
                tipos = obtener_tipos_por_ensayo(ensayo_tab)
                opciones_tipos = ["+ Nuevo tipo de kit"] + tipos
                tipo_sel = st.selectbox("Tipo de kit", opciones_tipos, key=f"tipo_sel_{i}")
                tipo_manual = ""
                if tipo_sel == "+ Nuevo tipo de kit":
                    tipo_manual = st.text_input("Nuevo tipo de kit", key=f"tipo_manual_{i}")

            cad_fecha = st.date_input("Caducidad", value=None, format="DD/MM/YYYY", key=f"cad_{i}")
            enviar_alta = st.form_submit_button("Guardar caja")

            if enviar_alta:
                codigo = normalizar_codigo(codigo_escaneado)
                tipo_kit = tipo_manual.strip() if tipo_sel == "+ Nuevo tipo de kit" else tipo_sel.strip()
                cad_str = formatear_fecha(cad_fecha) if cad_fecha else ""
                codigos_existentes = set(inventario["Codigo de barras"].astype(str).str.strip().str.upper().tolist())

                if not codigo:
                    codigo = generar_codigo_automatico_unico(ensayo_tab, tipo_kit, cad_str, codigos_existentes)

                if not tipo_kit:
                    st.error("Tipo de kit es obligatorio.")
                elif codigo in inventario["Codigo de barras"].astype(str).str.strip().str.upper().tolist():
                    st.error("Ese codigo ya existe en inventario activo.")
                else:
                    nueva = pd.DataFrame([
                        {
                            "Codigo de barras": codigo,
                            "Ensayo": ensayo_tab,
                            "Tipo de kit": tipo_kit,
                            "Caducidad": cad_str,
                        }
                    ])
                    inventario = pd.concat([inventario, nueva], ignore_index=True)
                    guardar_inventario(inventario)
                    registrar_tipo_ensayo(ensayo_tab, tipo_kit)
                    registrar_movimiento("ENTRADA", codigo, ensayo_tab, tipo_kit, cad_str, "Alta por escaneo")
                    st.success(f"Caja guardada en {ensayo_tab}: {codigo}")
                    st.rerun()

        st.markdown("**Salida por escaneo**")
        with st.form(f"form_salida_{i}", clear_on_submit=True):
            codigo_salida_raw = st.text_input(
                "Codigo para retirar",
                placeholder="Escanea aqui con la pistola",
                key=f"codigo_salida_{i}",
            )
            enviar_salida = st.form_submit_button("Retirar caja")

            if enviar_salida:
                codigo_salida = normalizar_codigo(codigo_salida_raw)
                if not codigo_salida:
                    st.error("Escanea un codigo valido.")
                else:
                    idx = inventario.index[
                        (inventario["Codigo de barras"].astype(str).str.strip().str.upper() == codigo_salida)
                        & (inventario["Ensayo"].astype(str).str.strip() == ensayo_tab)
                    ]

                    if len(idx) == 0:
                        st.error(f"Codigo no encontrado en inventario activo del ensayo {ensayo_tab}: {codigo_salida}")
                    else:
                        row = inventario.loc[idx[0]]
                        tipo_kit = str(row["Tipo de kit"])
                        cad = str(row["Caducidad"])

                        inventario = inventario.drop(index=idx[0]).reset_index(drop=True)
                        guardar_inventario(inventario)
                        registrar_movimiento("SALIDA", codigo_salida, ensayo_tab, tipo_kit, cad, "Retiro por escaneo")

                        st.success(f"Caja retirada de {ensayo_tab}: {codigo_salida} | Tipo: {tipo_kit}")
                        st.rerun()

        st.markdown("**Resumen de contabilidad del inventario activo**")
        total_activos = len(data_ensayo)
        st.write(f"Total de kits activos: {total_activos}")

        data_resumen = data_ensayo.copy()
        data_resumen["Tipo de kit"] = (
            data_resumen["Tipo de kit"].fillna("").astype(str).str.strip().replace("", "SIN TIPO")
        )

        hoy = date.today()
        data_resumen["_f_cad"] = data_resumen["Caducidad"].astype(str).apply(parsear_fecha)
        data_resumen["_caducada"] = data_resumen["_f_cad"].apply(lambda f: bool(f and f < hoy))
        data_resumen["_proxima"] = data_resumen["_f_cad"].apply(
            lambda f: bool(f and f >= hoy and (f - hoy).days <= DIAS_AVISO_CADUCIDAD)
        )

        resumen_tipos = (
            data_resumen.groupby("Tipo de kit", dropna=False)
            .agg(
                Cantidad=("Codigo de barras", "size"),
                Caducadas=("_caducada", "sum"),
                Proximas_a_caducar=("_proxima", "sum"),
            )
            .reset_index()
            .sort_values(by=["Cantidad", "Tipo de kit"], ascending=[False, True])
        )
        st.dataframe(resumen_tipos, use_container_width=True, hide_index=True)

        st.markdown("**Inventario activo del ensayo**")
        if data_ensayo.empty:
            st.info("No hay cajas activas en este ensayo.")
        else:
            filtro_inv = st.text_input(
                "Buscador en inventario (codigo, tipo o caducidad)",
                placeholder="Escribe para filtrar...",
                key=f"buscador_inv_{i}",
            ).strip()

            if filtro_inv:
                mascara = (
                    data_ensayo["Codigo de barras"].astype(str).str.contains(filtro_inv, case=False, na=False)
                    | data_ensayo["Tipo de kit"].astype(str).str.contains(filtro_inv, case=False, na=False)
                    | data_ensayo["Caducidad"].astype(str).str.contains(filtro_inv, case=False, na=False)
                )
                data_ensayo_vista = data_ensayo[mascara].copy()
            else:
                data_ensayo_vista = data_ensayo.copy()

            if data_ensayo_vista.empty:
                st.info("No hay resultados para el filtro aplicado.")

            for idx_row, row in data_ensayo_vista.iterrows():
                col1, col2, col3, col4, col5, col6 = st.columns([2, 1.5, 1.5, 1.5, 1, 1])
                
                with col1:
                    st.write(f"**{row['Codigo de barras']}**")
                with col2:
                    st.write(row['Tipo de kit'])
                with col3:
                    st.write(row['Caducidad'])
                with col4:
                    st.write(row['Ensayo'])
                
                with col5:
                    if st.button("Editar", key=f"edit_{ensayo_tab}_{idx_row}"):
                        st.session_state[f"edit_mode_{ensayo_tab}_{idx_row}"] = True
                
                with col6:
                    if st.button("Eliminar", key=f"del_{ensayo_tab}_{idx_row}"):
                        st.session_state[f"confirm_del_{ensayo_tab}_{idx_row}"] = True
                
                if st.session_state.get(f"edit_mode_{ensayo_tab}_{idx_row}"):
                    st.markdown("---")
                    st.subheader("Editar kit")
                    with st.form(f"form_edit_{ensayo_tab}_{idx_row}"):
                        nuevo_tipo = st.text_input("Tipo de kit", value=row['Tipo de kit'], key=f"edit_tipo_{ensayo_tab}_{idx_row}")
                        nueva_cad = st.date_input("Caducidad", value=parsear_fecha(row['Caducidad']), format="DD/MM/YYYY", key=f"edit_cad_{ensayo_tab}_{idx_row}")
                        
                        col_guardar, col_cancelar = st.columns(2)
                        with col_guardar:
                            guardar_edit = st.form_submit_button("Guardar cambios")
                        with col_cancelar:
                            cancelar_edit = st.form_submit_button("Cancelar")
                        
                        if guardar_edit:
                            nueva_cad_str = formatear_fecha(nueva_cad) if nueva_cad else ""
                            inventario.loc[inventario["Codigo de barras"].astype(str).str.strip().str.upper() == str(row['Codigo de barras']).upper(), "Tipo de kit"] = nuevo_tipo
                            inventario.loc[inventario["Codigo de barras"].astype(str).str.strip().str.upper() == str(row['Codigo de barras']).upper(), "Caducidad"] = nueva_cad_str
                            guardar_inventario(inventario)
                            st.success("Kit actualizado.")
                            st.session_state[f"edit_mode_{ensayo_tab}_{idx_row}"] = False
                            st.rerun()
                        
                        if cancelar_edit:
                            st.session_state[f"edit_mode_{ensayo_tab}_{idx_row}"] = False
                            st.rerun()
                
                if st.session_state.get(f"confirm_del_{ensayo_tab}_{idx_row}"):
                    st.markdown("---")
                    st.warning(f"¿Eliminar kit {row['Codigo de barras']}?")
                    col_si, col_no = st.columns(2)
                    with col_si:
                        if st.button("Sí, eliminar", key=f"confirm_del_si_{ensayo_tab}_{idx_row}"):
                            inventario = inventario[inventario["Codigo de barras"].astype(str).str.strip().str.upper() != str(row['Codigo de barras']).upper()].reset_index(drop=True)
                            guardar_inventario(inventario)
                            st.success("Kit eliminado.")
                            st.session_state[f"confirm_del_{ensayo_tab}_{idx_row}"] = False
                            st.rerun()
                    with col_no:
                        if st.button("Cancelar", key=f"confirm_del_no_{ensayo_tab}_{idx_row}"):
                            st.session_state[f"confirm_del_{ensayo_tab}_{idx_row}"] = False
                            st.rerun()

        st.markdown("**Historial del ensayo**")
        historial_ensayo = historial_global[
            historial_global["Ensayo"].astype(str).str.strip() == ensayo_tab
        ].copy()
        if historial_ensayo.empty:
            st.info("No hay movimientos registrados en este ensayo.")
        else:
            for idx_his, row_his in historial_ensayo.tail(100).iterrows():
                col1, col2, col3, col4, col5, col6, col7 = st.columns([1, 1, 1, 1.5, 1.5, 1, 0.8])
                
                with col1:
                    st.write(f"{row_his['Fecha']}")
                with col2:
                    st.write(f"{row_his['Hora']}")
                with col3:
                    st.write(f"{row_his['Accion']}")
                with col4:
                    st.write(f"{row_his['Codigo de barras']}")
                with col5:
                    st.write(f"{row_his['Tipo de kit']}")
                with col6:
                    st.write(f"{row_his['Caducidad']}")
                with col7:
                    if st.button("🗑️", key=f"del_his_{ensayo_tab}_{idx_his}"):
                        st.session_state[f"confirm_del_his_{ensayo_tab}_{idx_his}"] = True
                
                if st.session_state.get(f"confirm_del_his_{ensayo_tab}_{idx_his}"):
                    st.warning(f"¿Eliminar este registro?")
                    col_si, col_no = st.columns(2)
                    with col_si:
                        if st.button("Sí", key=f"confirm_del_his_si_{ensayo_tab}_{idx_his}"):
                            historial_global = historial_global.drop(index=idx_his).reset_index(drop=True)
                            guardar_historial(historial_global)
                            st.success("Registro eliminado.")
                            st.session_state[f"confirm_del_his_{ensayo_tab}_{idx_his}"] = False
                            st.rerun()
                    with col_no:
                        if st.button("No", key=f"confirm_del_his_no_{ensayo_tab}_{idx_his}"):
                            st.session_state[f"confirm_del_his_{ensayo_tab}_{idx_his}"] = False
                            st.rerun()

        st.markdown("**Impresion de pegatinas (A4, 3 x 8 = 24 por hoja)")
        hoy_date = date.today()
        entradas_hoy_ensayo = historial_global[
            (historial_global["Fecha"].astype(str).apply(parsear_fecha) == hoy_date) &
            (historial_global["Accion"].astype(str).str.strip().str.upper() == "ENTRADA") &
            (historial_global["Ensayo"].astype(str).str.strip() == ensayo_tab)
        ].copy()
        codigos_activos_ensayo = set(
            data_ensayo["Codigo de barras"].astype(str).str.strip().tolist()
        )
        entradas_hoy_ensayo = entradas_hoy_ensayo[
            entradas_hoy_ensayo["Codigo de barras"].astype(str).str.strip().isin(codigos_activos_ensayo)
        ].copy()

        if entradas_hoy_ensayo.empty:
            st.info("No hay kits activos de hoy en este ensayo para imprimir.")
        elif not BARCODE_DISPONIBLE:
            st.warning("Para generar etiquetas instala: pip install python-barcode pillow")
        else:
            opciones = []
            mapa = {}
            for _, row in entradas_hoy_ensayo.iterrows():
                etiqueta = f"{row['Codigo de barras']} | {row['Ensayo']} | {row['Tipo de kit']} | {row['Caducidad']}"
                opciones.append(etiqueta)
                mapa[etiqueta] = row

            seleccionar_todos = st.checkbox("Seleccionar todos los kits de hoy", value=True, key=f"todos_hoy_{i}")
            seleccionados = opciones if seleccionar_todos else st.multiselect("Selecciona kits a imprimir", opciones, key=f"multi_imprimir_{i}")

            if st.button("Generar archivo de pegatinas", key=f"btn_imprimir_{i}"):
                if not seleccionados:
                    st.error("Selecciona al menos un kit para imprimir.")
                else:
                    df_sel = pd.DataFrame([mapa[o] for o in seleccionados])
                    df_sel = df_sel[["Codigo de barras", "Ensayo", "Tipo de kit", "Caducidad"]].drop_duplicates(subset=["Codigo de barras"], keep="first")
                    html_doc = construir_html_pegatinas(df_sel)

                    st.download_button(
                        "Descargar pegatinas A4 (HTML)",
                        data=html_doc.encode("utf-8"),
                        file_name=f"pegatinas_{ensayo_tab}_{hoy_date.isoformat()}.html",
                        mime="text/html",
                        use_container_width=True,
                        key=f"download_imprimir_{i}",
                    )
                    st.info("Abre el HTML y usa Imprimir en A4 a escala 100% (rejilla 3 x 8 = 24 pegatinas por hoja).")
