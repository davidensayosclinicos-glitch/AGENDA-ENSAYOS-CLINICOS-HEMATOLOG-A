import streamlit as st
try:
    from streamlit_calendar import calendar
except ImportError:
    calendar = None
import sqlite3
from datetime import datetime, timedelta
import pandas as pd
import html
import streamlit.components.v1 as components
import os
import re
import base64
import webbrowser
import tempfile
import importlib
from urllib.parse import quote_plus

try:
    psycopg2 = importlib.import_module("psycopg2")
    PsycopgCursor = importlib.import_module("psycopg2.extensions").cursor
except ImportError:
    psycopg2 = None
    PsycopgCursor = None

try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Agenda Ensayos 2026", layout="wide")

if calendar is None:
    st.error(
        "Falta la dependencia `streamlit-calendar` en el entorno. "
        "Instala/declara `streamlit-calendar>=1.2.0` en `requirements.txt` y vuelve a desplegar."
    )
    st.stop()


def construir_estilos_app():
    estilo_fondo = "background-color: #dbeafe !important;"

    return f"""
        <style>
            :root {{
                --background-color: #dbeafe;
                --secondary-background-color: #eff6ff;
            }}
            html, body, .stApp, [data-testid="stApp"], [data-testid="stAppViewContainer"] {{
                {estilo_fondo}
            }}
            [data-testid="stAppViewContainer"] > .main {{
                {estilo_fondo}
            }}
            [data-testid="stAppViewContainer"] > .main .block-container {{
                background: transparent !important;
            }}
            [data-testid="stAppViewContainer"] > .main,
            [data-testid="stHeader"],
            [data-testid="stToolbar"] {{
                background: transparent !important;
            }}
            [data-testid="stHeader"] {{
                background-color: rgba(219, 234, 254, 0.9) !important;
            }}
            section[data-testid="stSidebar"] {{
                width: 240px !important;
            }}
            section[data-testid="stSidebar"] > div {{
                width: 240px !important;
                background: rgba(234, 244, 255, 0.9) !important;
            }}
            section[data-testid="stSidebar"] img {{
                width: 100% !important;
                max-width: none !important;
                height: auto !important;
            }}
            @media (max-width: 900px) {{
                section[data-testid="stSidebar"],
                section[data-testid="stSidebar"] > div {{
                    width: 220px !important;
                }}
            }}
            .fc, .fc .fc-scrollgrid, .fc .fc-view-harness {{
                background: #ffffff;
            }}
            .fc .fc-scrollgrid, .fc .fc-scrollgrid-section table {{
                border-color: #f1dede;
            }}
            div[data-baseweb="tab-list"] {{
                flex-wrap: wrap;
                gap: 0.25rem;
            }}
            button[data-baseweb="tab"] {{
                white-space: normal;
                height: auto;
                min-height: 2.25rem;
            }}
        </style>
    """

# --- ESTILOS ---
st.markdown(
        construir_estilos_app(),
        unsafe_allow_html=True,
)

# --- GESTIÓN DE MEMORIA (SESSION STATE) ---
if 'modo_formulario' not in st.session_state:
    st.session_state['modo_formulario'] = None # Puede ser 'nuevo' o 'ver'
if 'datos_seleccionados' not in st.session_state:
    st.session_state['datos_seleccionados'] = None
if 'paciente_seleccionado' not in st.session_state:
    st.session_state['paciente_seleccionado'] = None
if 'nombre_input' not in st.session_state:
    st.session_state['nombre_input'] = ""
if 'codigo_input' not in st.session_state:
    st.session_state['codigo_input'] = ""
if 'ensayo_input' not in st.session_state:
    st.session_state['ensayo_input'] = ""

# --- BASE DE DATOS ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def resolver_directorio(*candidatos):
    for ruta in candidatos:
        if ruta and os.path.isdir(ruta):
            return ruta
    return candidatos[0] if candidatos else ""


def resolver_archivo(*candidatos):
    for ruta in candidatos:
        if ruta and os.path.isfile(ruta):
            return ruta
    return ""


PDF_DIR = resolver_directorio(
    os.path.join(SCRIPT_DIR, "PROTOCOLOS ENFERMERIA"),
    r"N:\ENSAYOS\ENSAYOS\PROTOCOLOS ENFERMERIA",
    r"H:\ENSAYOS\ENSAYOS\PROTOCOLOS ENFERMERIA"
)
PDF_DIR_ENSAYO = resolver_directorio(
    os.path.join(SCRIPT_DIR, "PROTOCOLOS"),
    r"N:\ENSAYOS\ENSAYOS\PROTOCOLOS",
    r"H:\ENSAYOS\ENSAYOS\PROTOCOLOS"
)
IMG_DIR_ESQUEMAS = resolver_directorio(
    os.path.join(SCRIPT_DIR, "ESQUEMAS TRATAMIENTOS"),
    r"N:\ENSAYOS\ENSAYOS\ESQUEMAS TRATAMIENTOS",
    r"H:\ENSAYOS\ENSAYOS\ESQUEMAS TRATAMIENTOS"
)
APP_TIMEZONE = "Europe/Madrid"
DB_PATH = os.path.join(SCRIPT_DIR, "agenda_ensayos.db")
DB_BACKUP_DIR = os.path.join(SCRIPT_DIR, "backups_db")
APP_BUILD = datetime.fromtimestamp(os.path.getmtime(__file__)).strftime("%Y-%m-%d %H:%M")
LOGO_PATH = resolver_archivo(
    os.path.join(SCRIPT_DIR, "ChatGPT Image 10 mar 2026, 09_32_03.png"),
    os.path.join(SCRIPT_DIR, "ChatGPT Image 10 mar 2026, 09_22_55.png")
)


def leer_config(clave, default=None):
    valor_env = os.getenv(clave)
    if valor_env:
        return valor_env
    try:
        if clave in st.secrets:
            return st.secrets[clave]
    except Exception:
        pass
    return default


def extraer_database_url():
    def _limpiar_url(valor):
        if valor is None:
            return ""
        return str(valor).strip()

    def _construir_url_postgres_desde_bloque(bloque):
        if not bloque:
            return ""

        url_directa = _limpiar_url(bloque.get("url") if hasattr(bloque, "get") else None)
        if url_directa:
            return url_directa

        host = _limpiar_url(bloque.get("host") if hasattr(bloque, "get") else None)
        port = _limpiar_url(bloque.get("port") if hasattr(bloque, "get") else None) or "5432"
        dbname = _limpiar_url(
            (bloque.get("database") if hasattr(bloque, "get") else None)
            or (bloque.get("dbname") if hasattr(bloque, "get") else None)
        )
        user = _limpiar_url(
            (bloque.get("user") if hasattr(bloque, "get") else None)
            or (bloque.get("username") if hasattr(bloque, "get") else None)
        )
        password = _limpiar_url(bloque.get("password") if hasattr(bloque, "get") else None)
        sslmode = _limpiar_url(bloque.get("sslmode") if hasattr(bloque, "get") else None) or "require"

        if not (host and dbname and user):
            return ""

        credenciales = quote_plus(user)
        if password:
            credenciales += f":{quote_plus(password)}"

        return f"postgresql://{credenciales}@{host}:{port}/{dbname}?sslmode={sslmode}"

    # 1) Variables de entorno frecuentes.
    for clave in ("DATABASE_URL", "POSTGRES_URL", "POSTGRESQL_URL", "SUPABASE_DB_URL"):
        valor = _limpiar_url(os.getenv(clave))
        if valor:
            return valor

    # 2) Claves planas en st.secrets.
    try:
        for clave in ("DATABASE_URL", "POSTGRES_URL", "POSTGRESQL_URL", "SUPABASE_DB_URL"):
            if clave in st.secrets:
                valor = _limpiar_url(st.secrets[clave])
                if valor:
                    return valor
    except Exception:
        pass

    # 3) Estructuras anidadas tipicas de Streamlit secrets.
    try:
        if "connections" in st.secrets:
            conexiones = st.secrets["connections"]
            for nombre in ("postgresql", "postgres", "db"):
                if nombre in conexiones:
                    bloque = conexiones[nombre]
                    url = _construir_url_postgres_desde_bloque(bloque)
                    if url:
                        return url
    except Exception:
        pass

    # 4) Estructuras anidadas alternativas.
    try:
        for raiz in ("database", "postgres", "postgresql", "db"):
            if raiz in st.secrets:
                bloque = st.secrets[raiz]
                url = _construir_url_postgres_desde_bloque(bloque)
                if url:
                    return url
    except Exception:
        pass

    return ""


DATABASE_URL = extraer_database_url()
ALLOW_SQLITE_FALLBACK = str(leer_config("ALLOW_SQLITE_FALLBACK", "0")).strip().lower() in {
    "1", "true", "yes", "si"
}
SQLITE_DB_EXISTE = os.path.exists(DB_PATH)
_prefijos_postgres = ("postgres://", "postgresql://", "postgresql+psycopg2://")
_postgres_disponible = bool(
    DATABASE_URL
    and DATABASE_URL.startswith(_prefijos_postgres)
    and psycopg2 is not None
)

if _postgres_disponible:
    DB_BACKEND = "postgres"
elif ALLOW_SQLITE_FALLBACK or SQLITE_DB_EXISTE:
    DB_BACKEND = "sqlite"
else:
    DB_BACKEND = "sqlite"
    st.info(
        "Modo local SQLite activo (`agenda_ensayos.db`). "
        "Para produccion, configura `DATABASE_URL` en Streamlit Secrets."
    )

if DB_BACKEND == "sqlite" and not ALLOW_SQLITE_FALLBACK and SQLITE_DB_EXISTE:
    st.info(
        "Usando base local `agenda_ensayos.db` detectada en el proyecto. "
        "Para produccion, configura `DATABASE_URL` en Streamlit Secrets."
    )


def _adaptar_query_postgres(query):
    q = str(query).replace("?", "%s")
    q_up = q.upper()

    if "INSERT OR IGNORE INTO PACIENTES" in q_up:
        q = q.replace("INSERT OR IGNORE INTO pacientes", "INSERT INTO pacientes")
        if "ON CONFLICT" not in q.upper():
            q += " ON CONFLICT (codigo, ensayo) DO NOTHING"

    if "INSERT OR REPLACE INTO REVISION_OCULAR" in q_up:
        q = (
            "INSERT INTO revision_ocular (visita_id, fecha_cita, kva) "
            "VALUES (%s, %s, %s) "
            "ON CONFLICT (visita_id) DO UPDATE SET "
            "fecha_cita = EXCLUDED.fecha_cita, "
            "kva = EXCLUDED.kva"
        )

    return q


if PsycopgCursor is not None:
    class CursorCompatPostgres(PsycopgCursor):
        def execute(self, query, vars=None):
            super().execute(_adaptar_query_postgres(query), vars)
            return self

        def executemany(self, query, vars_list):
            super().executemany(_adaptar_query_postgres(query), vars_list)
            return self
else:
    CursorCompatPostgres = None


def connect_db():
    global DB_BACKEND
    if DB_BACKEND == "postgres":
        try:
            return psycopg2.connect(
                DATABASE_URL,
                cursor_factory=CursorCompatPostgres,
                connect_timeout=8,
            )
        except Exception:
            DB_BACKEND = "sqlite"
            if not st.session_state.get("_postgres_fallback_notificado"):
                st.session_state["_postgres_fallback_notificado"] = True
                st.warning(
                    "No se pudo conectar con PostgreSQL. "
                    "La app sigue en modo SQLite local (`agenda_ensayos.db`)."
                )
            return sqlite3.connect(DB_PATH)
    return sqlite3.connect(DB_PATH)


def snapshot_db(tag="autosave"):
    if DB_BACKEND != "sqlite":
        return
    try:
        if not os.path.exists(DB_PATH):
            return

        os.makedirs(DB_BACKUP_DIR, exist_ok=True)
        ts = ahora_local().strftime("%Y%m%d_%H%M%S")
        backup_name = f"agenda_ensayos_{tag}_{ts}.db"
        backup_path = os.path.join(DB_BACKUP_DIR, backup_name)

        src = connect_db()
        dst = sqlite3.connect(backup_path)
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()

        # Conserva un historial corto para no crecer sin limite.
        prefijo = f"agenda_ensayos_{tag}_"
        backups = sorted(
            [
                nombre for nombre in os.listdir(DB_BACKUP_DIR)
                if nombre.startswith(prefijo) and nombre.endswith(".db")
            ],
            reverse=True,
        )
        for viejo in backups[30:]:
            try:
                os.remove(os.path.join(DB_BACKUP_DIR, viejo))
            except OSError:
                pass
    except Exception:
        # Un fallo de backup no debe impedir el guardado principal.
        pass


def export_db_bytes():
    if DB_BACKEND != "sqlite":
        return None
    if not os.path.exists(DB_PATH):
        return None
    try:
        with open(DB_PATH, "rb") as f:
            return f.read()
    except OSError:
        return None


def restore_db_from_bytes(db_bytes):
    if DB_BACKEND != "sqlite":
        return False, "La restauracion manual aplica solo al modo SQLite local."
    if not db_bytes:
        return False, "Archivo vacio o invalido."
    try:
        # Guardamos un snapshot antes de sobrescribir para poder volver atras.
        snapshot_db("pre_restore")
        with open(DB_PATH, "wb") as f:
            f.write(db_bytes)
        return True, "Base de datos restaurada correctamente."
    except OSError:
        return False, "No se pudo escribir la base de datos de restauracion."


def fecha_hoy_local():
    if ZoneInfo is not None:
        try:
            return datetime.now(ZoneInfo(APP_TIMEZONE)).date()
        except Exception:
            pass
    return datetime.now().date()


def ahora_local():
    if ZoneInfo is not None:
        try:
            return datetime.now(ZoneInfo(APP_TIMEZONE))
        except Exception:
            pass
    return datetime.now()


def normalizar_texto_campo(valor):
    if valor is None:
        return ""
    texto = str(valor).strip()
    texto = re.sub(r"\s+", " ", texto)
    return texto


def nombre_a_iniciales(valor):
    texto = normalizar_texto_campo(valor)
    if not texto:
        return ""
    partes = re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+", texto)
    if not partes:
        return texto.upper()
    return " ".join(parte[0].upper() for parte in partes)


def normalizar_ensayo(valor):
    ensayo = normalizar_texto_campo(valor).upper()
    clave = re.sub(r"[\s\-_/]+", "", ensayo)

    if clave in {"GEM21", "GEM2021"}:
        return "GEM21"

    match_rgn = re.fullmatch(r"RGN[\s\-_/]*([0-9]+)", ensayo)
    if match_rgn:
        return match_rgn.group(1)
    return ensayo


def normalizar_clave_paciente(valor):
    texto = normalizar_texto_campo(valor).lower()
    return re.sub(r"[\s\-_/]+", "", texto)


def clave_paciente_unificada(codigo, nombre, ensayo):
    ensayo_norm = normalizar_clave_paciente(ensayo)
    codigo_norm = normalizar_clave_paciente(codigo)
    nombre_norm = normalizar_clave_paciente(nombre)
    if not ensayo_norm:
        return ""
    if codigo_norm:
        return f"{ensayo_norm}|codigo|{codigo_norm}"
    if nombre_norm:
        return f"{ensayo_norm}|nombre|{nombre_norm}"
    return ""


def guardar_o_actualizar_paciente(cursor, codigo, nombre, ensayo):
    codigo = normalizar_texto_campo(codigo)
    nombre = nombre_a_iniciales(nombre)
    ensayo = normalizar_ensayo(ensayo)
    clave_nueva = clave_paciente_unificada(codigo, nombre, ensayo)
    if not clave_nueva:
        return

    existentes = cursor.execute(
        "SELECT id, codigo, nombre, ensayo FROM pacientes ORDER BY id DESC"
    ).fetchall()

    id_existente = None
    for row in existentes:
        clave_existente = clave_paciente_unificada(row[1], row[2], row[3])
        if clave_existente == clave_nueva:
            id_existente = row[0]
            break

    if id_existente:
        cursor.execute(
            "UPDATE pacientes SET codigo = ?, nombre = ?, ensayo = ? WHERE id = ?",
            (codigo, nombre, ensayo, id_existente)
        )
    else:
        cursor.execute(
            "INSERT OR IGNORE INTO pacientes (codigo, nombre, ensayo) VALUES (?, ?, ?)",
            (codigo, nombre, ensayo)
        )


def unificar_pacientes_duplicados(cursor):
    filas = cursor.execute(
        "SELECT id, codigo, nombre, ensayo FROM pacientes ORDER BY id DESC"
    ).fetchall()
    claves_vistas = set()
    ids_borrar = []

    for fila in filas:
        fila_id, codigo, nombre, ensayo = fila
        codigo_limpio = normalizar_texto_campo(codigo)
        nombre_limpio = normalizar_texto_campo(nombre)
        ensayo_limpio = normalizar_texto_campo(ensayo)
        clave = clave_paciente_unificada(codigo_limpio, nombre_limpio, ensayo_limpio)

        if not clave:
            continue
        if clave in claves_vistas:
            ids_borrar.append(fila_id)
            continue

        claves_vistas.add(clave)
        cursor.execute(
            "UPDATE pacientes SET codigo = ?, nombre = ?, ensayo = ? WHERE id = ?",
            (codigo_limpio, nombre_limpio, ensayo_limpio, fila_id)
        )

    if ids_borrar:
        cursor.executemany(
            "DELETE FROM pacientes WHERE id = ?",
            [(fila_id,) for fila_id in ids_borrar]
        )


def sincronizar_pacientes_desde_visitas(cursor):
    visitas = cursor.execute(
        "SELECT codigo, nombre, ensayo FROM visitas ORDER BY id DESC"
    ).fetchall()

    # Construimos el estado deseado por clave unificada para evitar vaciar toda la tabla.
    deseados = {}
    for codigo, nombre, ensayo in visitas:
        codigo_limpio = normalizar_texto_campo(codigo)
        nombre_limpio = nombre_a_iniciales(nombre)
        ensayo_limpio = normalizar_ensayo(ensayo)
        clave = clave_paciente_unificada(codigo_limpio, nombre_limpio, ensayo_limpio)
        if clave and clave not in deseados:
            deseados[clave] = (codigo_limpio, nombre_limpio, ensayo_limpio)

    existentes = cursor.execute(
        "SELECT id, codigo, nombre, ensayo FROM pacientes ORDER BY id ASC"
    ).fetchall()

    ids_borrar = []
    for fila_id, codigo, nombre, ensayo in existentes:
        codigo_limpio = normalizar_texto_campo(codigo)
        nombre_limpio = nombre_a_iniciales(nombre)
        ensayo_limpio = normalizar_ensayo(ensayo)
        clave = clave_paciente_unificada(codigo_limpio, nombre_limpio, ensayo_limpio)

        if not clave or clave not in deseados:
            ids_borrar.append(fila_id)
            continue

        objetivo = deseados.pop(clave)
        if (codigo_limpio, nombre_limpio, ensayo_limpio) != objetivo:
            cursor.execute(
                "UPDATE pacientes SET codigo = ?, nombre = ?, ensayo = ? WHERE id = ?",
                (objetivo[0], objetivo[1], objetivo[2], fila_id)
            )

    for codigo, nombre, ensayo in deseados.values():
        cursor.execute(
            "INSERT OR IGNORE INTO pacientes (codigo, nombre, ensayo) VALUES (?, ?, ?)",
            (codigo, nombre, ensayo)
        )

    if ids_borrar:
        cursor.executemany(
            "DELETE FROM pacientes WHERE id = ?",
            [(fila_id,) for fila_id in ids_borrar]
        )

    unificar_pacientes_duplicados(cursor)


def _es_deadlock_error(exc):
    if psycopg2 is None:
        return False
    errores = getattr(psycopg2, "errors", None)
    deadlock_cls = getattr(errores, "DeadlockDetected", None)
    return deadlock_cls is not None and isinstance(exc, deadlock_cls)


def normalizar_ensayos_existentes(cursor):
    visitas = cursor.execute("SELECT id, ensayo FROM visitas").fetchall()
    for visita_id, ensayo in visitas:
        ensayo_norm = normalizar_ensayo(ensayo)
        if ensayo_norm != ("" if ensayo is None else str(ensayo)):
            cursor.execute(
                "UPDATE visitas SET ensayo = ? WHERE id = ?",
                (ensayo_norm, visita_id)
            )

    checklist = cursor.execute("SELECT id, ensayo FROM checklist_items").fetchall()
    for item_id, ensayo in checklist:
        ensayo_norm = normalizar_ensayo(ensayo)
        if ensayo_norm != ("" if ensayo is None else str(ensayo)):
            cursor.execute(
                "UPDATE checklist_items SET ensayo = ? WHERE id = ?",
                (ensayo_norm, item_id)
            )


def anonimizar_nombres_existentes(cursor):
    visitas = cursor.execute("SELECT id, nombre FROM visitas").fetchall()
    for visita_id, nombre in visitas:
        nombre_norm = nombre_a_iniciales(nombre)
        nombre_actual = "" if nombre is None else str(nombre)
        if nombre_norm != nombre_actual:
            cursor.execute(
                "UPDATE visitas SET nombre = ? WHERE id = ?",
                (nombre_norm, visita_id)
            )

    pacientes = cursor.execute("SELECT id, nombre FROM pacientes").fetchall()
    for paciente_id, nombre in pacientes:
        nombre_norm = nombre_a_iniciales(nombre)
        nombre_actual = "" if nombre is None else str(nombre)
        if nombre_norm != nombre_actual:
            cursor.execute(
                "UPDATE pacientes SET nombre = ? WHERE id = ?",
                (nombre_norm, paciente_id)
            )


def eliminar_ensayos_sin_pacientes(cursor):
    filas_pacientes = cursor.execute(
        "SELECT codigo, nombre, ensayo FROM pacientes"
    ).fetchall()
    ensayos_validos = set()
    for codigo, nombre, ensayo in filas_pacientes:
        codigo_norm = normalizar_clave_paciente(codigo)
        nombre_norm = normalizar_clave_paciente(nombre)
        ensayo_norm = normalizar_clave_paciente(ensayo)
        if ensayo_norm and (codigo_norm or nombre_norm):
            ensayos_validos.add(ensayo_norm)

    filas_checklist = cursor.execute("SELECT id, ensayo FROM checklist_items").fetchall()
    ids_borrar = []
    for item_id, ensayo in filas_checklist:
        if normalizar_clave_paciente(ensayo) not in ensayos_validos:
            ids_borrar.append(item_id)

    if ids_borrar:
        cursor.executemany(
            "DELETE FROM checklist_items WHERE id = ?",
            [(item_id,) for item_id in ids_borrar]
        )


def init_db():
    conn = connect_db()
    c = conn.cursor()
    if DB_BACKEND == "postgres":
        c.execute(
            '''
            CREATE TABLE IF NOT EXISTS visitas (
                id BIGSERIAL PRIMARY KEY,
                fecha TEXT NOT NULL,
                nombre TEXT,
                codigo TEXT,
                ensayo TEXT,
                ciclo TEXT,
                kits TEXT,
                tablet BOOLEAN,
                medula BOOLEAN,
                otras_pruebas TEXT,
                comentarios TEXT
            )
            '''
        )
        c.execute(
            '''
            CREATE TABLE IF NOT EXISTS revision_ocular (
                id BIGSERIAL PRIMARY KEY,
                visita_id BIGINT UNIQUE,
                fecha_cita TEXT,
                kva INTEGER
            )
            '''
        )
        c.execute(
            '''
            CREATE TABLE IF NOT EXISTS pacientes (
                id BIGSERIAL PRIMARY KEY,
                codigo TEXT,
                nombre TEXT,
                ensayo TEXT,
                UNIQUE(codigo, ensayo)
            )
            '''
        )
        c.execute(
            '''
            CREATE TABLE IF NOT EXISTS checklist_items (
                id BIGSERIAL PRIMARY KEY,
                ensayo TEXT,
                item TEXT,
                done BOOLEAN DEFAULT FALSE
            )
            '''
        )
        c.execute(
            '''
            CREATE TABLE IF NOT EXISTS notas_esquemas (
                id BIGSERIAL PRIMARY KEY,
                nombre_esquema TEXT UNIQUE,
                nota TEXT,
                fecha_modificacion TEXT
            )
            '''
        )
        c.execute(
            '''
            CREATE TABLE IF NOT EXISTS notas_enfermeria (
                id BIGSERIAL PRIMARY KEY,
                fecha_nota TEXT NOT NULL,
                texto TEXT NOT NULL,
                urgencia TEXT NOT NULL,
                creado_en TEXT NOT NULL
            )
            '''
        )
    else:
        c.execute('''
            CREATE TABLE IF NOT EXISTS visitas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL,
                nombre TEXT,
                codigo TEXT,
                ensayo TEXT,
                ciclo TEXT,
                kits TEXT,
                tablet BOOLEAN,
                medula BOOLEAN,
                otras_pruebas TEXT,
                comentarios TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS revision_ocular (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                visita_id INTEGER UNIQUE,
                fecha_cita TEXT,
                kva INTEGER,
                FOREIGN KEY(visita_id) REFERENCES visitas(id)
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS pacientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo TEXT,
                nombre TEXT,
                ensayo TEXT,
                UNIQUE(codigo, ensayo)
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS checklist_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ensayo TEXT,
                item TEXT,
                done BOOLEAN DEFAULT 0
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS notas_esquemas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre_esquema TEXT UNIQUE,
                nota TEXT,
                fecha_modificacion TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS notas_enfermeria (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha_nota TEXT NOT NULL,
                texto TEXT NOT NULL,
                urgencia TEXT NOT NULL,
                creado_en TEXT NOT NULL
            )
        ''')

    # En PostgreSQL y despliegues concurrentes, serializamos el mantenimiento
    # para evitar contencion y deadlocks entre sesiones de Streamlit.
    if DB_BACKEND == "postgres":
        lock_id = 20260309
        try:
            c.execute("SELECT pg_try_advisory_xact_lock(?)", (lock_id,))
            fila_lock = c.fetchone()
            lock_adquirido = bool(fila_lock and fila_lock[0])
        except Exception:
            lock_adquirido = False

        if not lock_adquirido:
            conn.commit()
            conn.close()
            return

    try:
        anonimizar_nombres_existentes(c)
        normalizar_ensayos_existentes(c)
        sincronizar_pacientes_desde_visitas(c)
        eliminar_ensayos_sin_pacientes(c)
    except Exception as exc:
        if _es_deadlock_error(exc):
            # En arranque con varias sesiones, evitamos que un deadlock puntual derribe la app.
            conn.rollback()
        else:
            conn.rollback()
            conn.close()
            raise
    conn.commit()
    conn.close()

def guardar_visita(fecha, data):
    data = data.copy()
    data['nombre'] = nombre_a_iniciales(data.get('nombre'))
    data['codigo'] = normalizar_texto_campo(data.get('codigo'))
    data['ensayo'] = normalizar_ensayo(data.get('ensayo'))
    conn = connect_db()
    c = conn.cursor()
    c.execute('''
        INSERT INTO visitas (fecha, nombre, codigo, ensayo, ciclo, kits, tablet, medula, otras_pruebas, comentarios)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (fecha, data['nombre'], data['codigo'], data['ensayo'], data['ciclo'], 
          data['kits'], data['tablet'], data['medula'], data['otras_pruebas'], data['comentarios']))
    guardar_o_actualizar_paciente(c, data.get('codigo'), data.get('nombre'), data.get('ensayo'))
    unificar_pacientes_duplicados(c)
    eliminar_ensayos_sin_pacientes(c)
    conn.commit()
    conn.close()
    invalidar_cache_lecturas()
    snapshot_db("pacientes")

def actualizar_visita(id_visita, fecha, data):
    data = data.copy()
    data['nombre'] = nombre_a_iniciales(data.get('nombre'))
    data['codigo'] = normalizar_texto_campo(data.get('codigo'))
    data['ensayo'] = normalizar_ensayo(data.get('ensayo'))
    conn = connect_db()
    c = conn.cursor()
    c.execute('''
        UPDATE visitas
        SET fecha = ?, nombre = ?, codigo = ?, ensayo = ?, ciclo = ?,
            kits = ?, tablet = ?, medula = ?, otras_pruebas = ?, comentarios = ?
        WHERE id = ?
    ''', (
        fecha, data['nombre'], data['codigo'], data['ensayo'], data['ciclo'],
        data['kits'], data['tablet'], data['medula'], data['otras_pruebas'], data['comentarios'],
        id_visita
    ))
    guardar_o_actualizar_paciente(c, data.get('codigo'), data.get('nombre'), data.get('ensayo'))
    unificar_pacientes_duplicados(c)
    eliminar_ensayos_sin_pacientes(c)
    conn.commit()
    conn.close()
    invalidar_cache_lecturas()
    snapshot_db("pacientes")

@st.cache_data(show_spinner=False)
def get_visitas():
    conn = connect_db()
    try:
        df = pd.read_sql("SELECT * FROM visitas", conn)
    except:
        df = pd.DataFrame()
    conn.close()
    return df

@st.cache_data(show_spinner=False)
def get_pacientes_unicos():
    conn = connect_db()
    try:
        df = pd.read_sql("SELECT codigo, nombre, ensayo FROM pacientes", conn)
    except Exception:
        df = pd.DataFrame()
    conn.close()

    def deduplicar_pacientes(df_in):
        if df_in.empty:
            return df_in
        df_local = df_in.copy()
        for col in ["codigo", "nombre", "ensayo"]:
            if col not in df_local.columns:
                df_local[col] = ""
            if col == "ensayo":
                df_local[col] = df_local[col].fillna("").astype(str).apply(normalizar_ensayo)
            elif col == "nombre":
                df_local[col] = df_local[col].fillna("").astype(str).apply(nombre_a_iniciales)
            else:
                df_local[col] = df_local[col].fillna("").astype(str).apply(normalizar_texto_campo)
        df_local["_clave"] = df_local.apply(
            lambda row: clave_paciente_unificada(row["codigo"], row["nombre"], row["ensayo"]),
            axis=1
        )
        df_local["_tiene_codigo"] = df_local["codigo"].astype(str).str.strip().ne("")
        df_local = df_local[df_local["_clave"] != ""]
        if df_local.empty:
            return pd.DataFrame(columns=["codigo", "nombre", "ensayo"])
        df_local = df_local.sort_values(by=["_tiene_codigo"], ascending=False)
        df_local = df_local.drop_duplicates(subset=["_clave"], keep="first")
        return df_local[["codigo", "nombre", "ensayo"]].reset_index(drop=True)

    if df.empty:
        df_visitas = get_visitas()
        if df_visitas.empty:
            return pd.DataFrame()
        base = df_visitas[["codigo", "nombre", "ensayo"]].dropna(how='all')
        return deduplicar_pacientes(base)
    return deduplicar_pacientes(df.dropna(how='all'))


@st.cache_data(show_spinner=False)
def get_ensayos_existentes():
    ensayos = set()

    df_pacientes = get_pacientes_unicos()
    if not df_pacientes.empty and "ensayo" in df_pacientes.columns:
        for ensayo in df_pacientes["ensayo"].tolist():
            ensayo_norm = normalizar_ensayo(ensayo)
            if ensayo_norm:
                ensayos.add(ensayo_norm)

    if not ensayos:
        df_visitas = get_visitas()
        if not df_visitas.empty and "ensayo" in df_visitas.columns:
            for ensayo in df_visitas["ensayo"].tolist():
                ensayo_norm = normalizar_ensayo(ensayo)
                if ensayo_norm:
                    ensayos.add(ensayo_norm)

    return sorted(ensayos)

def borrar_visita(id_visita):
    conn = connect_db()
    c = conn.cursor()
    c.execute("DELETE FROM visitas WHERE id=?", (id_visita,))
    sincronizar_pacientes_desde_visitas(c)
    eliminar_ensayos_sin_pacientes(c)
    conn.commit()
    conn.close()
    invalidar_cache_lecturas()
    snapshot_db("pacientes")

@st.cache_data(show_spinner=False)
def get_checklist_items(ensayo):
    ensayo = normalizar_ensayo(ensayo)
    conn = connect_db()
    df = pd.read_sql(
        "SELECT id, item, done FROM checklist_items WHERE ensayo = ? ORDER BY id",
        conn,
        params=(ensayo,)
    )
    conn.close()
    return df

def add_checklist_item(ensayo, item):
    ensayo = normalizar_ensayo(ensayo)
    conn = connect_db()
    c = conn.cursor()
    c.execute(
        "INSERT INTO checklist_items (ensayo, item, done) VALUES (?, ?, 0)",
        (ensayo, item)
    )
    conn.commit()
    conn.close()
    invalidar_cache_lecturas()

def add_checklist_items_bulk(ensayo, items):
    ensayo = normalizar_ensayo(ensayo)
    if not items:
        return
    conn = connect_db()
    c = conn.cursor()
    existentes = set(
        row[0] for row in c.execute(
            "SELECT item FROM checklist_items WHERE ensayo = ?",
            (ensayo,)
        ).fetchall()
    )
    nuevos = [(ensayo, item) for item in items if item not in existentes]
    if nuevos:
        c.executemany(
            "INSERT INTO checklist_items (ensayo, item, done) VALUES (?, ?, 0)",
            nuevos
        )
    conn.commit()
    conn.close()
    invalidar_cache_lecturas()

def set_checklist_done(item_id, done):
    conn = connect_db()
    c = conn.cursor()
    c.execute("UPDATE checklist_items SET done = ? WHERE id = ?", (int(done), item_id))
    conn.commit()
    conn.close()
    invalidar_cache_lecturas()

def delete_checklist_item(item_id):
    conn = connect_db()
    c = conn.cursor()
    c.execute("DELETE FROM checklist_items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    invalidar_cache_lecturas()


def add_nota_enfermeria(fecha_nota, texto, urgencia):
    conn = connect_db()
    c = conn.cursor()
    creado_en = ahora_local().isoformat(timespec="seconds")
    c.execute(
        """
        INSERT INTO notas_enfermeria (fecha_nota, texto, urgencia, creado_en)
        VALUES (?, ?, ?, ?)
        """,
        (fecha_nota, texto, urgencia, creado_en)
    )
    conn.commit()
    conn.close()
    invalidar_cache_lecturas()


@st.cache_data(show_spinner=False)
def get_notas_enfermeria():
    conn = connect_db()
    df = pd.read_sql(
        """
        SELECT id, fecha_nota, texto, urgencia, creado_en
        FROM notas_enfermeria
        ORDER BY creado_en ASC, id ASC
        """,
        conn
    )
    conn.close()
    return df


def delete_nota_enfermeria(nota_id):
    conn = connect_db()
    c = conn.cursor()
    c.execute("DELETE FROM notas_enfermeria WHERE id = ?", (nota_id,))
    conn.commit()
    conn.close()
    invalidar_cache_lecturas()


def parse_datetime_iso(valor):
    if valor is None:
        return None
    texto = str(valor).strip()
    if not texto:
        return None
    try:
        if texto.endswith("Z"):
            texto = texto[:-1] + "+00:00"
        dt = datetime.fromisoformat(texto)
        if dt.tzinfo is not None:
            if ZoneInfo is not None:
                return dt.astimezone(ZoneInfo(APP_TIMEZONE))
            return dt.astimezone()
        return dt
    except (ValueError, TypeError):
        return None


def formatear_latencia_desde_creacion(creado_en):
    creado_dt = parse_datetime_iso(creado_en)
    if creado_dt is None:
        return "N/D"

    ahora = ahora_local()
    if creado_dt.tzinfo is None and ahora.tzinfo is not None:
        creado_dt = creado_dt.replace(tzinfo=ahora.tzinfo)
    if creado_dt.tzinfo is not None and ahora.tzinfo is None:
        ahora = ahora.replace(tzinfo=creado_dt.tzinfo)

    delta = ahora - creado_dt
    segundos = int(max(delta.total_seconds(), 0))

    dias = segundos // 86400
    horas = (segundos % 86400) // 3600
    minutos = (segundos % 3600) // 60

    if dias > 0:
        return f"{dias}d {horas}h {minutos}m"
    if horas > 0:
        return f"{horas}h {minutos}m"
    return f"{minutos}m"

def guardar_revision_ocular(visita_id, fecha_cita, kva):
    conn = connect_db()
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO revision_ocular (visita_id, fecha_cita, kva) VALUES (?, ?, ?)",
        (visita_id, fecha_cita, kva)
    )
    conn.commit()
    conn.close()
    invalidar_cache_lecturas()

@st.cache_data(show_spinner=False)
def get_revision_ocular(visita_id):
    conn = connect_db()
    c = conn.cursor()
    c.execute("SELECT fecha_cita, kva FROM revision_ocular WHERE visita_id=?", (visita_id,))
    row = c.fetchone()
    conn.close()
    return row


@st.cache_data(show_spinner=False)
def get_revisiones_oculares_df():
    conn = connect_db()
    df = pd.read_sql(
        "SELECT visita_id, fecha_cita, kva FROM revision_ocular",
        conn
    )
    conn.close()
    return df


def invalidar_cache_lecturas():
    get_visitas.clear()
    get_pacientes_unicos.clear()
    get_ensayos_existentes.clear()
    get_checklist_items.clear()
    get_notas_enfermeria.clear()
    get_revision_ocular.clear()
    get_revisiones_oculares_df.clear()

def render_print_dialog(texto, titulo):
        texto_html = html.escape(texto).replace("\n", "<br>")
        plantilla = f"""
        <html>
            <head>
                <title>{html.escape(titulo)}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 24px; }}
                    h1 {{ font-size: 18px; margin-bottom: 12px; }}
                    .contenido {{ font-size: 14px; line-height: 1.4; }}
                </style>
            </head>
            <body>
                <h1>{html.escape(titulo)}</h1>
                <div class="contenido">{texto_html}</div>
                <script>
                    window.onload = function() {{
                        window.print();
                    }};
                </script>
            </body>
        </html>
        """
        components.html(plantilla, height=0)

def formatear_fecha_visita(fecha_iso):
    if not fecha_iso:
        return ""
    try:
        valor = str(fecha_iso).strip()
        if "T" in valor:
            if valor.endswith("Z"):
                valor = valor[:-1] + "+00:00"
            dt = datetime.fromisoformat(valor)
            if dt.tzinfo is not None:
                if ZoneInfo is not None:
                    dt = dt.astimezone(ZoneInfo(APP_TIMEZONE))
                else:
                    dt = dt.astimezone()
            return dt.strftime("%d/%m/%Y")
        dt = datetime.fromisoformat(valor)
        return dt.strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        try:
            valor = str(fecha_iso).strip()
            fecha_base = valor.split("T", 1)[0][:10]
            dt = datetime.strptime(fecha_base, "%Y-%m-%d")
            return dt.strftime("%d/%m/%Y")
        except (ValueError, TypeError):
            return str(fecha_iso)

def parse_fecha_iso(fecha_iso):
    if not fecha_iso:
        return None

    valor = str(fecha_iso).strip()
    if not valor:
        return None

    if "T" in valor:
        try:
            valor_iso = valor
            if valor_iso.endswith("Z"):
                valor_iso = valor_iso[:-1] + "+00:00"
            dt = datetime.fromisoformat(valor_iso)
            if dt.tzinfo is not None:
                if ZoneInfo is not None:
                    dt = dt.astimezone(ZoneInfo(APP_TIMEZONE))
                else:
                    dt = dt.astimezone()
            return dt.date()
        except (ValueError, TypeError):
            pass

    candidato = valor.split(" ", 1)[0][:10]
    formatos = (
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y/%m/%d",
    )
    for formato in formatos:
        try:
            return datetime.strptime(candidato, formato).date()
        except (ValueError, TypeError):
            continue
    return None

@st.cache_data(show_spinner=False)
def generar_visita_teorica_2274(df_visitas):
    if df_visitas.empty:
        return []
    df = df_visitas.copy()
    df = df[df["ensayo"].astype(str).str.contains("2274", case=False, na=False)]
    if df.empty:
        return []

    df["_fecha_dt"] = df["fecha"].apply(parse_fecha_iso)
    df = df.dropna(subset=["_fecha_dt", "codigo"])
    if df.empty:
        return []

    ultimas = df.sort_values("_fecha_dt").groupby("codigo", as_index=False).tail(1)
    eventos = []

    def siguiente_ciclo_y_delta(ciclo_raw):
        if not ciclo_raw:
            return None, None
        ciclo_txt = str(ciclo_raw).upper().replace(" ", "")
        if "C0D1" in ciclo_txt:
            return "C0D8", 7
        if "C0D8" in ciclo_txt:
            return "C1D1", 7

        ciclo_num = None
        dia_num = None
        if "C" in ciclo_txt:
            try:
                ciclo_num = int(ciclo_txt.split("C", 1)[1].split("D", 1)[0])
            except (ValueError, IndexError):
                ciclo_num = None
        if "D" in ciclo_txt:
            try:
                dia_num = int(ciclo_txt.split("D", 1)[1])
            except (ValueError, IndexError):
                dia_num = None

        if ciclo_num is None:
            return None, None
        if dia_num is None:
            dia_num = 1

        if ciclo_num <= 2:
            if dia_num in (1, 8, 15):
                return f"C{ciclo_num}D{dia_num + 7}", 7
            return f"C{ciclo_num + 1}D1", 7

        return f"C{ciclo_num + 1}D1", 28

    for _, row in ultimas.iterrows():
        codigo = str(row["codigo"]).strip()
        base = row["_fecha_dt"]
        if not codigo or base is None:
            continue
        siguiente_ciclo, delta = siguiente_ciclo_y_delta(row.get("ciclo"))
        if not siguiente_ciclo or not delta:
            continue
        fecha = base + timedelta(days=int(delta) + 1)
        eventos.append({
            "title": f"Teorica {siguiente_ciclo} | {codigo}",
            "start": fecha.isoformat(),
            "allDay": True,
            "backgroundColor": "#7bbcff",
            "borderColor": "#2f6fbf"
        })

    return eventos


@st.cache_data(show_spinner=False)
def construir_eventos_calendario(df_visitas):
    eventos = []
    if df_visitas.empty:
        return eventos

    for _, row in df_visitas.iterrows():
        titulo_evento = f"🆔 {row['codigo']} | {row['ensayo']}"
        if row['medula']:
            titulo_evento += " 🩸"

        event = {
            "title": titulo_evento,
            "start": row['fecha'],
            "allDay": True,
            "extendedProps": {
                "id": row['id'],
                "nombre": row['nombre'],
                "ciclo": row['ciclo'],
                "medula": row['medula'],
                "ensayo": row['ensayo']
            },
            "backgroundColor": "#ff4b4b" if row['medula'] else "#3788d8"
        }
        eventos.append(event)

    eventos.extend(generar_visita_teorica_2274(df_visitas))
    return eventos

def listar_pdfs(directorio):
    if not os.path.isdir(directorio):
        return []
    archivos = [
        f for f in os.listdir(directorio)
        if f.lower().endswith(".pdf") and os.path.isfile(os.path.join(directorio, f))
    ]
    return sorted(archivos)

def listar_imagenes(directorio):
    if not os.path.isdir(directorio):
        return []
    extensiones = (".png", ".jpg", ".jpeg", ".webp", ".bmp")
    archivos = [
        f for f in os.listdir(directorio)
        if f.lower().endswith(extensiones) and os.path.isfile(os.path.join(directorio, f))
    ]
    return sorted(archivos)

@st.cache_data(show_spinner=False)
def extraer_texto_pdf(ruta_pdf):
    if PdfReader is None:
        return ""
    try:
        reader = PdfReader(ruta_pdf)
        partes = []
        for page in reader.pages:
            partes.append(page.extract_text() or "")
        return "\n".join(partes)
    except Exception:
        return ""

def pdf_contiene_texto(ruta_pdf, consulta):
    texto = extraer_texto_pdf(ruta_pdf)
    return consulta in texto.lower()

def render_pdf_viewer(ruta_pdf, initial_page=1):
    try:
        with open(ruta_pdf, "rb") as archivo:
            contenido = archivo.read()
        b64 = base64.b64encode(contenido).decode("ascii")
        pagina_inicial = initial_page if initial_page and initial_page > 0 else 1
        html_viewer = f"""
        <div style="border: 1px solid #e2cfcf; border-radius: 6px; padding: 8px; background: #fff;">
            <div style="display: flex; gap: 8px; align-items: center; margin-bottom: 8px; flex-wrap: wrap; font-size: 12px;">
                <button id="prev">Anterior</button>
                <button id="next">Siguiente</button>
                <span>Pagina: <span id="page_num">1</span> / <span id="page_count">?</span></span>
                <span id="loading" style="margin-left: auto; color: #8a6d6d;">Cargando...</span>
            </div>
            <div id="pdf-container" style="max-height: 700px; overflow: auto;">
                <canvas id="the-canvas" style="width: 100%;"></canvas>
            </div>
        </div>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
        <script>
            const pdfData = atob("{b64}");
            const pdfBytes = new Uint8Array(pdfData.length);
            for (let i = 0; i < pdfData.length; i++) {{
                pdfBytes[i] = pdfData.charCodeAt(i);
            }}

            const pdfjsLib = window['pdfjs-dist/build/pdf'];
            pdfjsLib.GlobalWorkerOptions.workerSrc =
                "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";

            let pdfDoc = null;
            let pageNum = {pagina_inicial};
            const scale = 0.7;
            const canvas = document.getElementById('the-canvas');
            const ctx = canvas.getContext('2d');

            function renderPage(num) {{
                pdfDoc.getPage(num).then(function(page) {{
                    const viewport = page.getViewport({{ scale: scale }});
                    const container = document.getElementById('pdf-container');
                    const containerWidth = container.clientWidth - 16;
                    const fitScale = containerWidth / viewport.width;
                    const finalViewport = page.getViewport({{ scale: scale * fitScale }});

                    canvas.height = finalViewport.height;
                    canvas.width = finalViewport.width;

                    const renderContext = {{
                        canvasContext: ctx,
                        viewport: finalViewport
                    }};
                    page.render(renderContext).promise.then(function() {{
                        document.getElementById('loading').textContent = '';
                    }});
                    document.getElementById('page_num').textContent = num;
                }});
            }}

            function queueRenderPage(num) {{
                renderPage(num);
            }}

            function onPrevPage() {{
                if (pageNum <= 1) return;
                pageNum--;
                queueRenderPage(pageNum);
            }}

            function onNextPage() {{
                if (pageNum >= pdfDoc.numPages) return;
                pageNum++;
                queueRenderPage(pageNum);
            }}

            document.getElementById('prev').addEventListener('click', onPrevPage);
            document.getElementById('next').addEventListener('click', onNextPage);

            pdfjsLib.getDocument({{ data: pdfBytes, disableStream: true, disableRange: true }}).promise.then(function(pdfDoc_) {{
                pdfDoc = pdfDoc_;
                document.getElementById('page_count').textContent = pdfDoc.numPages;
                if (pageNum < 1) pageNum = 1;
                if (pageNum > pdfDoc.numPages) pageNum = pdfDoc.numPages;
                renderPage(pageNum);
            }});
        </script>
        """
        components.html(html_viewer, height=740)
    except OSError:
        st.error("No se pudo abrir el PDF seleccionado.")

@st.cache_data(show_spinner=False)
def buscar_paginas_pdf(ruta_pdf, consulta):
    if PdfReader is None:
        return []
    try:
        reader = PdfReader(ruta_pdf)
        paginas = []
        for idx, page in enumerate(reader.pages, start=1):
            texto = page.extract_text() or ""
            if consulta in texto.lower():
                paginas.append(idx)
        return paginas
    except Exception:
        return []

@st.cache_data(show_spinner=False)
def contar_paginas_pdf(ruta_pdf):
    if PdfReader is None:
        return 1
    try:
        reader = PdfReader(ruta_pdf)
        return len(reader.pages)
    except Exception:
        return 1


def obtener_fecha_objetivo_portada():
    fecha_objetivo = fecha_hoy_local() + timedelta(days=1)
    while fecha_objetivo.weekday() >= 5:  # 5=sábado, 6=domingo
        fecha_objetivo += timedelta(days=1)
    return fecha_objetivo


def render_resumen_manana():
    manana = obtener_fecha_objetivo_portada()
    fecha_mostrar = manana
    st.caption(f"Fecha: {fecha_mostrar.strftime('%d/%m/%Y')}")

    df_visitas_portada = get_visitas()
    if df_visitas_portada.empty:
        st.info("No hay visitas registradas.")
        return

    df_visitas_portada = df_visitas_portada.copy()
    df_visitas_portada["_fecha_dt"] = df_visitas_portada["fecha"].apply(parse_fecha_iso)
    df_manana = df_visitas_portada[df_visitas_portada["_fecha_dt"] == manana].copy()

    if df_manana.empty:
        df_proximas = df_visitas_portada[df_visitas_portada["_fecha_dt"].notna()].copy()
        df_proximas = df_proximas[df_proximas["_fecha_dt"] >= manana].sort_values("_fecha_dt")
        if df_proximas.empty:
            st.success("No hay pacientes programados para mañana.")
            return
        fecha_mostrar = df_proximas.iloc[0]["_fecha_dt"]
        df_manana = df_proximas[df_proximas["_fecha_dt"] == fecha_mostrar].copy()
        st.caption(f"Mostrando próxima fecha con pacientes: {fecha_mostrar.strftime('%d/%m/%Y')}")

    df_rev = get_revisiones_oculares_df()

    if not df_rev.empty:
        df_manana = df_manana.merge(
            df_rev,
            how="left",
            left_on="id",
            right_on="visita_id"
        )
    else:
        df_manana["fecha_cita"] = None
        df_manana["kva"] = None

    if fecha_mostrar == manana:
        st.info(f"Pacientes de mañana: {len(df_manana)}")
    else:
        st.info(f"Pacientes ({fecha_mostrar.strftime('%d/%m/%Y')}): {len(df_manana)}")

    for _, row in df_manana.sort_values(by=["ensayo", "codigo"], na_position="last").iterrows():
        codigo = "" if pd.isna(row.get("codigo")) else str(row.get("codigo"))
        nombre = "" if pd.isna(row.get("nombre")) else str(row.get("nombre"))
        ensayo = "" if pd.isna(row.get("ensayo")) else str(row.get("ensayo"))
        ciclo = "" if pd.isna(row.get("ciclo")) else str(row.get("ciclo"))

        tareas = []
        if ciclo.strip():
            tareas.append(f"Ciclo/Día: {ciclo}")
        if bool(row.get("medula")):
            tareas.append("Punción de médula")
        if bool(row.get("tablet")):
            tareas.append("Preparar tablet")

        kits = "" if pd.isna(row.get("kits")) else str(row.get("kits")).strip()
        if kits:
            tareas.append(f"Kits/medicación: {kits}")

        otras = "" if pd.isna(row.get("otras_pruebas")) else str(row.get("otras_pruebas")).strip()
        if otras:
            tareas.append(f"Otras pruebas: {otras}")

        fecha_rev = parse_fecha_iso(row.get("fecha_cita")) if "fecha_cita" in row else None
        kva = row.get("kva") if "kva" in row else None
        if fecha_rev:
            detalle_rev = f"Revisión ocular: {fecha_rev.strftime('%d/%m/%Y')}"
            if kva is not None and not pd.isna(kva):
                detalle_rev += f" (KVA {int(kva)})"
            tareas.append(detalle_rev)

        comentarios = "" if pd.isna(row.get("comentarios")) else str(row.get("comentarios")).strip()
        if comentarios:
            tareas.append(f"Comentarios: {comentarios}")

        if not tareas:
            tareas.append("Sin tareas adicionales registradas")

        titulo = f"🆔 {codigo} | {nombre} | {ensayo}".strip(" |")
        with st.expander(titulo, expanded=True):
            for tarea in tareas:
                st.write(f"• {tarea}")

# Inicializamos DB una vez por sesion para evitar coste en cada rerun.
if not st.session_state.get("_db_inicializada", False):
    init_db()
    st.session_state["_db_inicializada"] = True

# --- INTERFAZ PRINCIPAL ---
if LOGO_PATH:
    st.sidebar.image(LOGO_PATH, use_container_width=True)
else:
    st.sidebar.caption("Logo no encontrado")
st.sidebar.markdown("### 📅 Agenda de Pacientes - Ensayos Clínicos 2026")

secciones_principales = [
    "Agenda",
    "Prot. enfermeria",
    "Prot. ensayo",
    "Ficha paciente",
    "Check list",
    "Notas enfermeria",
    "Esquemas",
]
seccion_activa = st.sidebar.radio("Navegación", options=secciones_principales, key="seccion_principal")

if seccion_activa == "Prot. enfermeria":
    st.subheader("📄 Protocolos de Enfermería")
    col_list, col_view = st.columns([1, 1])
    with col_list:
        pdfs = listar_pdfs(PDF_DIR)
        st.caption(f"Carpeta: {PDF_DIR}")
        if not pdfs:
            st.warning("No se encontraron PDFs en la carpeta configurada.")
            pdf_seleccionado = None
        else:
            pdf_seleccionado = st.selectbox("Selecciona un PDF", pdfs, key="pdf_enfermeria")
    with col_view:
        if pdf_seleccionado:
            ruta_pdf = os.path.join(PDF_DIR, pdf_seleccionado)
            render_pdf_viewer(ruta_pdf)

if seccion_activa == "Prot. ensayo":
    st.subheader("📄 Protocolos de Ensayo")
    col_list, col_view = st.columns([1, 1])
    with col_list:
        pdfs = listar_pdfs(PDF_DIR_ENSAYO)
        st.caption(f"Carpeta: {PDF_DIR_ENSAYO}")
        if not pdfs:
            st.warning("No se encontraron PDFs en la carpeta configurada.")
            pdf_seleccionado = None
        else:
            pdf_seleccionado = st.selectbox("Selecciona un PDF", pdfs, key="pdf_ensayo")
            busqueda = st.text_input("Buscar dentro del PDF", key="buscar_protocolos_ensayo")
    with col_view:
        if pdf_seleccionado:
            ruta_pdf = os.path.join(PDF_DIR_ENSAYO, pdf_seleccionado)
            total_paginas = contar_paginas_pdf(ruta_pdf)
            page_key = f"pagina_actual_{pdf_seleccionado}"
            match_key = f"match_idx_{pdf_seleccionado}"
            if page_key not in st.session_state:
                st.session_state[page_key] = 1
            if busqueda:
                filtro = busqueda.strip().lower()
                if filtro:
                    with st.spinner("Buscando en el PDF..."):
                        paginas = buscar_paginas_pdf(ruta_pdf, filtro)
                    if paginas:
                        st.success(f"Coincidencias en paginas: {', '.join(str(p) for p in paginas)}")
                        if match_key not in st.session_state:
                            st.session_state[match_key] = 0
                        match_cols = st.columns([1, 1])
                        if match_cols[0].button("◀ Coincidencia", key=f"prev_match_{pdf_seleccionado}"):
                            if st.session_state[match_key] > 0:
                                st.session_state[match_key] -= 1
                            st.session_state[page_key] = paginas[st.session_state[match_key]]
                            st.session_state[f"page_input_{pdf_seleccionado}"] = st.session_state[page_key]
                        if match_cols[1].button("Coincidencia ▶", key=f"next_match_{pdf_seleccionado}"):
                            if st.session_state[match_key] < len(paginas) - 1:
                                st.session_state[match_key] += 1
                            st.session_state[page_key] = paginas[st.session_state[match_key]]
                            st.session_state[f"page_input_{pdf_seleccionado}"] = st.session_state[page_key]
                    else:
                        st.warning("No se encontraron coincidencias en este PDF.")
            page_input_key = f"page_input_{pdf_seleccionado}"
            nav_cols = st.columns([1, 1, 2])
            if nav_cols[0].button("◀", key=f"prev_page_{pdf_seleccionado}"):
                if st.session_state[page_key] > 1:
                    st.session_state[page_key] -= 1
                    st.session_state[page_input_key] = st.session_state[page_key]
            if nav_cols[1].button("▶", key=f"next_page_{pdf_seleccionado}"):
                if st.session_state[page_key] < total_paginas:
                    st.session_state[page_key] += 1
                    st.session_state[page_input_key] = st.session_state[page_key]
            pagina_manual = nav_cols[2].number_input(
                "Pagina",
                min_value=1,
                max_value=total_paginas,
                value=st.session_state[page_key],
                step=1,
                key=page_input_key
            )
            st.session_state[page_key] = pagina_manual
            render_pdf_viewer(ruta_pdf, initial_page=st.session_state[page_key])

if seccion_activa == "Esquemas":
    st.subheader("🧩 Esquemas de tratamiento")
    col_list, col_view = st.columns([1, 2])
    with col_list:
        imagenes = listar_imagenes(IMG_DIR_ESQUEMAS)
        st.caption(f"Carpeta: {IMG_DIR_ESQUEMAS}")
        if not imagenes:
            st.warning("No se encontraron imagenes en la carpeta configurada.")
            img_sel = None
        else:
            img_sel = st.selectbox("Selecciona una imagen", imagenes, key="esquema_img")
    with col_view:
        if img_sel:
            ruta_img = os.path.join(IMG_DIR_ESQUEMAS, img_sel)
            st.image(ruta_img, use_container_width=True)
            
            # --- NOTAS DEL ESQUEMA ---
            st.markdown("---")
            st.markdown("### 📝 Notas del Esquema")
            
            # Cargar nota existente
            conn = connect_db()
            c = conn.cursor()
            c.execute("SELECT nota FROM notas_esquemas WHERE nombre_esquema = ?", (img_sel,))
            resultado = c.fetchone()
            nota_actual = resultado[0] if resultado else ""
            conn.close()
            
            # Campo de texto para la nota
            nota_nueva = st.text_area(
                "Escribe tus notas sobre este esquema:",
                value=nota_actual,
                height=150,
                key=f"nota_{img_sel}"
            )
            
            # Botones de acción
            col1, col2 = st.columns(2)
            
            with col1:
                # Botón para guardar
                if st.button("💾 Guardar Nota", key=f"guardar_nota_{img_sel}"):
                    conn = connect_db()
                    c = conn.cursor()
                    fecha_mod = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    c.execute("""
                        INSERT INTO notas_esquemas (nombre_esquema, nota, fecha_modificacion)
                        VALUES (?, ?, ?)
                        ON CONFLICT(nombre_esquema) DO UPDATE SET
                        nota = excluded.nota,
                        fecha_modificacion = excluded.fecha_modificacion
                    """, (img_sel, nota_nueva, fecha_mod))
                    conn.commit()
                    conn.close()
                    st.success("✅ Nota guardada correctamente")
            
            with col2:
                # Botón para generar informe imprimible
                if st.button("🖨️ Generar Informe", key=f"imprimir_{img_sel}"):
                    # Convertir imagen a base64 para embeber en HTML
                    with open(ruta_img, "rb") as img_file:
                        img_base64 = base64.b64encode(img_file.read()).decode()
                    
                    # Obtener extensión de la imagen
                    ext = os.path.splitext(ruta_img)[1].lower()
                    mime_type = "image/jpeg" if ext in [".jpg", ".jpeg"] else "image/png"
                    
                    # Generar HTML
                    html_informe = f"""
                    <!DOCTYPE html>
                    <html lang="es">
                    <head>
                        <meta charset="utf-8">
                        <title>Esquema de Tratamiento - {img_sel}</title>
                        <style>
                            * {{
                                margin: 0;
                                padding: 0;
                                box-sizing: border-box;
                            }}
                            body {{
                                font-family: 'Arial', 'Segoe UI', sans-serif;
                                line-height: 1.6;
                                color: #1f2937;
                                background: white;
                                padding: 30px;
                            }}
                            .container {{
                                max-width: 1000px;
                                margin: 0 auto;
                            }}
                            .header {{
                                text-align: center;
                                border-bottom: 3px solid #dc2626;
                                padding-bottom: 20px;
                                margin-bottom: 30px;
                            }}
                            .header h1 {{
                                font-size: 24px;
                                color: #dc2626;
                                font-weight: bold;
                                margin-bottom: 5px;
                            }}
                            .header p {{
                                font-size: 12px;
                                color: #666;
                                margin: 3px 0;
                            }}
                            .esquema-box {{
                                margin-bottom: 30px;
                                padding: 15px;
                                background: #fef2f2;
                                border-left: 4px solid #dc2626;
                                border-radius: 4px;
                            }}
                            .esquema-box h2 {{
                                font-size: 16px;
                                color: #dc2626;
                                margin-bottom: 10px;
                            }}
                            .imagen-container {{
                                text-align: center;
                                margin: 20px 0;
                                padding: 10px;
                                background: white;
                                border: 1px solid #e5e7eb;
                                border-radius: 4px;
                            }}
                            .imagen-container img {{
                                max-width: 100%;
                                height: auto;
                                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                            }}
                            .notas-box {{
                                margin-top: 30px;
                                padding: 20px;
                                background: #f9fafb;
                                border-left: 4px solid #3b82f6;
                                border-radius: 4px;
                            }}
                            .notas-box h3 {{
                                font-size: 15px;
                                color: #3b82f6;
                                margin-bottom: 15px;
                            }}
                            .notas-content {{
                                font-size: 12px;
                                line-height: 1.8;
                                white-space: pre-wrap;
                                color: #374151;
                            }}
                            .footer {{
                                margin-top: 40px;
                                padding-top: 20px;
                                border-top: 2px solid #e5e7eb;
                                text-align: center;
                                font-size: 10px;
                                color: #999;
                            }}
                            @media print {{
                                body {{
                                    margin: 0;
                                    padding: 15px;
                                }}
                                .container {{
                                    max-width: 100%;
                                }}
                            }}
                        </style>
                    </head>
                    <body>
                        <div class="container">
                            <div class="header">
                                <h1>📋 ESQUEMA DE TRATAMIENTO</h1>
                                <p>Documento generado: {datetime.now().strftime('%d/%m/%Y - %H:%M')}</p>
                            </div>
                            
                            <div class="esquema-box">
                                <h2>{img_sel}</h2>
                            </div>
                            
                            <div class="imagen-container">
                                <img src="data:{mime_type};base64,{img_base64}" alt="{img_sel}">
                            </div>
                            
                            <div class="notas-box">
                                <h3>📝 Notas del Esquema</h3>
                                <div class="notas-content">{html.escape(nota_nueva) if nota_nueva else "Sin notas"}</div>
                            </div>
                            
                            <div class="footer">
                                <p>Documento confidencial - Uso exclusivo para personal autorizado</p>
                            </div>
                        </div>
                    </body>
                    </html>
                    """
                    
                    # Guardar HTML en archivo temporal
                    html_file = os.path.join(tempfile.gettempdir(), f"esquema_{img_sel.replace('.', '_')}.html")
                    with open(html_file, "w", encoding="utf-8") as f:
                        f.write(html_informe)
                    
                    # Abrir en navegador
                    webbrowser.open(f"file:///{html_file}")
                    st.success("✅ Informe generado. Se abrirá en tu navegador.")
                    st.info("💡 Presiona Ctrl+P (o Cmd+P en Mac) para imprimir o guardar como PDF")
            
            # Mostrar fecha de última modificación
            if nota_actual:
                conn = connect_db()
                c = conn.cursor()
                c.execute("SELECT fecha_modificacion FROM notas_esquemas WHERE nombre_esquema = ?", (img_sel,))
                resultado = c.fetchone()
                conn.close()
                if resultado:
                    st.caption(f"Última modificación: {resultado[0]}")

if seccion_activa == "Ficha paciente":
    st.subheader("🧾 Ficha del paciente")
    df_visitas = get_visitas()
    if df_visitas.empty:
        st.info("No hay visitas registradas para mostrar la ficha.")
    else:
        df_pacientes = get_pacientes_unicos()
        if df_pacientes.empty:
            st.info("No hay pacientes guardados.")
        else:
            df_pacientes = df_pacientes.copy()
            df_pacientes["ensayo"] = df_pacientes["ensayo"].fillna("").astype(str)
            ensayos = sorted([e for e in df_pacientes["ensayo"].unique() if e.strip()])
            ensayo_sel = st.selectbox(
                "Ensayo",
                options=["Todos"] + ensayos,
                key="ficha_ensayo"
            )
            nombre_filtro = st.text_input(
                "Nombre del paciente (puedes escribir)",
                key="ficha_nombre"
            )

            df_filtrado = df_pacientes.copy()
            if ensayo_sel != "Todos":
                df_filtrado = df_filtrado[df_filtrado["ensayo"].astype(str) == ensayo_sel]
            if nombre_filtro.strip():
                df_filtrado = df_filtrado[
                    df_filtrado["nombre"].astype(str).str.contains(nombre_filtro, case=False, na=False)
                ]

            opciones_pacientes = []
            mapa_pacientes = {}
            for _, row in df_filtrado.iterrows():
                codigo = "" if pd.isna(row['codigo']) else str(row['codigo'])
                nombre = "" if pd.isna(row['nombre']) else str(row['nombre'])
                ensayo = "" if pd.isna(row['ensayo']) else str(row['ensayo'])
                etiqueta = f"{codigo} | {nombre} | {ensayo}".strip(" |")
                opciones_pacientes.append(etiqueta)
                mapa_pacientes[etiqueta] = {
                    "codigo": codigo,
                    "nombre": nombre,
                    "ensayo": ensayo
                }

            if not opciones_pacientes:
                st.warning("No hay pacientes que coincidan con los filtros.")
                seleccion = None
            else:
                seleccion = st.selectbox(
                    "Paciente",
                    options=opciones_pacientes,
                    key="ficha_paciente"
                )

            datos_sel = mapa_pacientes.get(seleccion, {}) if seleccion else {}
            codigo_sel = datos_sel.get("codigo")
            nombre_sel = datos_sel.get("nombre")
            ensayo_sel = datos_sel.get("ensayo")

            df_ficha = pd.DataFrame()
            ensayo_sel_norm = normalizar_clave_paciente(ensayo_sel)
            if codigo_sel or nombre_sel:
                base = df_visitas.copy()
                base["_codigo_norm"] = base["codigo"].fillna("").astype(str).apply(normalizar_clave_paciente)
                base["_nombre_norm"] = base["nombre"].fillna("").astype(str).apply(normalizar_clave_paciente)
                base["_ensayo_norm"] = base["ensayo"].fillna("").astype(str).apply(normalizar_clave_paciente)

                filtro = base["_ensayo_norm"] == ensayo_sel_norm
                codigo_sel_norm = normalizar_clave_paciente(codigo_sel)
                nombre_sel_norm = normalizar_clave_paciente(nombre_sel)

                if codigo_sel_norm:
                    filtro = filtro & (base["_codigo_norm"] == codigo_sel_norm)
                elif nombre_sel_norm:
                    filtro = filtro & (base["_nombre_norm"] == nombre_sel_norm)

                df_ficha = base[filtro].copy()

                if not df_ficha.empty:
                    df_rev = get_revisiones_oculares_df()
                    df_ficha = df_ficha.merge(
                        df_rev,
                        how="left",
                        left_on="id",
                        right_on="visita_id"
                    )
                    df_ficha = df_ficha.rename(columns={"fecha_cita": "fecha_revision"})
                    df_ficha.drop(columns=["visita_id"], inplace=True, errors="ignore")

            if df_ficha.empty and nombre_sel:
                nombre_sel_norm = normalizar_clave_paciente(nombre_sel)
                base = df_visitas.copy()
                base["_nombre_norm"] = base["nombre"].fillna("").astype(str).apply(normalizar_clave_paciente)
                base["_ensayo_norm"] = base["ensayo"].fillna("").astype(str).apply(normalizar_clave_paciente)
                df_ficha = base[
                    (base["_nombre_norm"] == nombre_sel_norm)
                    & (base["_ensayo_norm"] == ensayo_sel_norm)
                ].copy()
                if not df_ficha.empty:
                    df_rev = get_revisiones_oculares_df()
                    df_ficha = df_ficha.merge(
                        df_rev,
                        how="left",
                        left_on="id",
                        right_on="visita_id"
                    )
                    df_ficha = df_ficha.rename(columns={"fecha_cita": "fecha_revision"})
                    df_ficha.drop(columns=["visita_id"], inplace=True, errors="ignore")

            if df_ficha.empty:
                st.warning("No se encontraron visitas para este paciente.")
            else:
                df_ficha = df_ficha.copy()
                df_ficha["_fecha_dt"] = df_ficha["fecha"].apply(parse_fecha_iso)
                hoy = fecha_hoy_local()
                colores = {}
                for idx, fecha_dt in df_ficha["_fecha_dt"].items():
                    if not fecha_dt:
                        colores[idx] = ""
                    elif fecha_dt < hoy:
                        colores[idx] = "#d7f2d7"
                    elif fecha_dt == hoy:
                        colores[idx] = "#fff3cd"
                    else:
                        colores[idx] = "#f8d7da"

                df_ficha["fecha"] = df_ficha["fecha"].apply(formatear_fecha_visita)
                df_ficha["fecha_revision"] = df_ficha["fecha_revision"].apply(formatear_fecha_visita)
                df_ficha["tablet"] = df_ficha["tablet"].apply(lambda v: "Si" if v else "No")
                df_ficha["medula"] = df_ficha["medula"].apply(lambda v: "Si" if v else "No")

                df_ficha = df_ficha.rename(
                    columns={
                        "fecha": "VISITA (FECHA)",
                        "codigo": "CODIGO",
                        "nombre": "NOMBRE",
                        "ensayo": "ENSAYO",
                        "ciclo": "CICLO",
                        "kits": "KITS",
                        "tablet": "TABLET",
                        "medula": "MEDULA",
                        "otras_pruebas": "OTRAS PRUEBAS",
                        "comentarios": "COMENTARIOS",
                        "fecha_revision": "REVISION OCULAR (FECHA)",
                        "kva": "KVA"
                    }
                )
                df_ficha = df_ficha[
                    [
                        "VISITA (FECHA)",
                        "CODIGO",
                        "NOMBRE",
                        "ENSAYO",
                        "CICLO",
                        "KITS",
                        "TABLET",
                        "MEDULA",
                        "OTRAS PRUEBAS",
                        "COMENTARIOS",
                        "REVISION OCULAR (FECHA)",
                        "KVA"
                    ]
                ]

                def colorear_filas(row):
                    color = colores.get(row.name, "")
                    if not color:
                        return [""] * len(row)
                    return [f"background-color: {color}"] * len(row)

                st.caption("Verde: visitas realizadas. Amarillo: hoy. Rojo: pendientes.")
                st.dataframe(df_ficha.style.apply(colorear_filas, axis=1), use_container_width=True)

if seccion_activa == "Check list":
    st.subheader("✅ Check List por ensayo")
    df_pacientes = get_pacientes_unicos()
    ensayos = []
    if not df_pacientes.empty:
        df_pacientes = df_pacientes.copy()
        df_pacientes["ensayo"] = df_pacientes["ensayo"].fillna("").astype(str)
        ensayos = sorted([e for e in df_pacientes["ensayo"].unique() if e.strip()])

    ensayo_sel = st.selectbox(
        "Ensayo",
        options=ensayos if ensayos else [""],
        key="checklist_ensayo"
    )

    if not ensayo_sel:
        st.info("No hay ensayos disponibles. Registra al menos una visita.")
    else:
        df_pacientes_ensayo = pd.DataFrame()
        if not df_pacientes.empty:
            df_pacientes_ensayo = df_pacientes[df_pacientes["ensayo"].astype(str) == ensayo_sel].copy()

        opciones_pac = ["Selecciona paciente"]
        mapa_pac = {}
        if not df_pacientes_ensayo.empty:
            for _, row in df_pacientes_ensayo.iterrows():
                codigo = "" if pd.isna(row['codigo']) else str(row['codigo'])
                nombre = "" if pd.isna(row['nombre']) else str(row['nombre'])
                etiqueta = f"{codigo} | {nombre}".strip(" |")
                opciones_pac.append(etiqueta)
                mapa_pac[etiqueta] = {
                    "codigo": codigo,
                    "nombre": nombre
                }

        paciente_sel = st.selectbox(
            "Paciente",
            options=opciones_pac,
            key="checklist_paciente"
        )
        datos_paciente = mapa_pac.get(paciente_sel, {}) if paciente_sel != "Selecciona paciente" else {}

        if ensayo_sel.strip() == "2274":
            if st.button("Cargar checklist de screening 2274"):
                checklist_2274 = [
                    "Consentimiento informado firmado y fechado",
                    "Asignacion de codigo de participante",
                    "Datos demograficos",
                    "Historia medica / quirurgica / oncologica completa",
                    "Revision de criterios de inclusion y exclusion",
                    "Altura",
                    "Peso corporal",
                    "Exploracion fisica completa",
                    "Constantes vitales: Presion arterial",
                    "Constantes vitales: Presion arterial ortostatica (screening)",
                    "Constantes vitales: Frecuencia cardiaca",
                    "Constantes vitales: Temperatura",
                    "Constantes vitales: Frecuencia respiratoria",
                    "Constantes vitales: Saturacion O2",
                    "ECOG Performance Status",
                    "Exploracion neurologica breve",
                    "ICE score (screening ICANS)",
                    "ECG de 12 derivaciones",
                    "Ecocardiograma o MUGA (FEVI)",
                    "NT-proBNP",
                    "Troponina cardiaca (cTnT)",
                    "Estadio Mayo para amiloidosis AL",
                    "Hematologia: Hemoglobina",
                    "Hematologia: Hematocrito",
                    "Hematologia: Recuento de eritrocitos (RBC)",
                    "Hematologia: Recuento total de leucocitos (WBC)",
                    "Hematologia: Neutrofilos",
                    "Hematologia: Linfocitos",
                    "Hematologia: Monocitos",
                    "Hematologia: Eosinofilos",
                    "Hematologia: Basofilos",
                    "Hematologia: Recuento de plaquetas",
                    "Hematologia: Celulas plasmaticas (si aplica)",
                    "Bioquimica: Sodio",
                    "Bioquimica: Potasio",
                    "Bioquimica: Cloruro",
                    "Bioquimica: CO2 / Bicarbonato",
                    "Bioquimica: Calcio",
                    "Bioquimica: Fosforo",
                    "Bioquimica: Glucosa",
                    "Bioquimica: Urea (BUN)",
                    "Bioquimica: Creatinina (eGFR CKD-EPI)",
                    "Bioquimica: Acido urico",
                    "Bioquimica: AST",
                    "Bioquimica: ALT",
                    "Bioquimica: Fosfatasa alcalina (ALP)",
                    "Bioquimica: LDH",
                    "Bioquimica: CPK",
                    "Bioquimica: Amilasa",
                    "Bioquimica: Lipasa",
                    "Bioquimica: Bilirrubina total y directa",
                    "Bioquimica: Proteinas totales",
                    "Bioquimica: Albumina",
                    "Orina: Color / aspecto",
                    "Orina: Densidad",
                    "Orina: pH",
                    "Orina: Proteinas",
                    "Orina: Glucosa",
                    "Orina: Cetonas",
                    "Orina: Bilirrubina",
                    "Orina: Sangre",
                    "Orina: Nitritos",
                    "Orina: Esterasa leucocitaria",
                    "Orina: Sedimento urinario (RBC, WBC, cilindros, bacterias, cristales, levaduras, celulas epiteliales)",
                    "Serologias: HIV",
                    "Serologias: Hepatitis B (HBV)",
                    "Serologias: Hepatitis C (HCV)",
                    "Serologias: CMV PCR",
                    "Serologias: LTBI / tuberculosis latente (solo cohortes 3-4)",
                    "Coagulacion: PT / INR",
                    "Coagulacion: aPTT / PTT",
                    "Enfermedad: SPEP",
                    "Enfermedad: Inmunofijacion serica (SIFE)",
                    "Enfermedad: UPEP (orina 24 h)",
                    "Enfermedad: Inmunofijacion urinaria (UIFE)",
                    "Enfermedad: dFLC",
                    "Enfermedad: Ratio FLC involucrada / no involucrada",
                    "Enfermedad: Cuantificacion de Ig no involucradas (IgG, IgA, IgM ± IgE)",
                    "Enfermedad: beta2-microglobulina",
                    "Medula osea: Aspirado de medula osea",
                    "Medula osea: Biopsia de medula osea",
                    "Medula osea: Evaluacion de enfermedad",
                    "Medula osea: MRD (segun SoA)",
                    "Imagen: PET-CT corporal completo (preferente)",
                    "Imagen: TC corporal completo de baja dosis (alternativa)",
                    "Imagen: Evaluacion de lesiones liticas / plasmocitomas",
                    "Otras: Ecografia abdominal (solo si ALP basal >1.5 x LSN)",
                    "Otras: Biomarcadores exploratorios (si aplica)",
                    "Otras: PROs (si aplica segun cohorte)",
                    "Confirmacion final: Todas las pruebas obligatorias completadas",
                    "Confirmacion final: Resultados revisados por el investigador",
                    "Confirmacion final: Criterios de inclusion cumplidos",
                    "Confirmacion final: Ningun criterio de exclusion presente",
                    "Confirmacion final: Participante apto / no apto para inicio de tratamiento"
                ]
                add_checklist_items_bulk(ensayo_sel, checklist_2274)
                st.success("Checklist 2274 cargado.")
                st.rerun()

        col_add, col_spacer = st.columns([3, 1])
        with col_add:
            nuevo_item = st.text_input("Nuevo item", key="checklist_nuevo_item")
            if st.button("Agregar item"):
                if nuevo_item.strip():
                    add_checklist_item(ensayo_sel, nuevo_item.strip())
                    st.rerun()
                else:
                    st.warning("El item no puede estar vacio.")

        df_items = get_checklist_items(ensayo_sel)
        if df_items.empty:
            st.info("No hay items para este ensayo.")
        else:
            for _, row in df_items.iterrows():
                cols = st.columns([8, 1])
                with cols[0]:
                    estado = st.checkbox(
                        row["item"],
                        value=bool(row["done"]),
                        key=f"chk_{row['id']}"
                    )
                    if estado != bool(row["done"]):
                        set_checklist_done(int(row["id"]), estado)
                with cols[1]:
                    if st.button("🗑️", key=f"del_{row['id']}"):
                        delete_checklist_item(int(row["id"]))
                        st.rerun()

            if st.button("Imprimir checklist"):
                nombre_paciente = datos_paciente.get("nombre", "")
                codigo_paciente = datos_paciente.get("codigo", "")
                header = f"Checklist - Ensayo {ensayo_sel}"
                if nombre_paciente or codigo_paciente:
                    header += f"\nPaciente: {codigo_paciente} {nombre_paciente}".strip()
                lineas = [header, "", "Items:"]
                for _, row in df_items.iterrows():
                    marca = "[x]" if bool(row["done"]) else "[ ]"
                    lineas.append(f"{marca} {row['item']}")
                render_print_dialog("\n".join(lineas), f"Checklist {ensayo_sel}")

if seccion_activa == "Notas enfermeria":
    st.subheader("📝 Notas de enfermería")

    urgencias = {
        "verde": {"label": "Verde (baja)", "icono": "🟢", "color": "#15803d"},
        "amarillo": {"label": "Amarillo (media)", "icono": "🟡", "color": "#ca8a04"},
        "rojo": {"label": "Rojo (alta)", "icono": "🔴", "color": "#dc2626"},
    }

    with st.form("form_nota_enfermeria", clear_on_submit=True):
        fecha_nota = st.date_input("Fecha de la nota", value=fecha_hoy_local(), key="nota_enf_fecha")
        texto_nota = st.text_area("Texto libre", key="nota_enf_texto", height=120)
        urgencia_sel = st.selectbox(
            "Urgencia (semáforo)",
            options=list(urgencias.keys()),
            format_func=lambda u: f"{urgencias[u]['icono']} {urgencias[u]['label']}",
            key="nota_enf_urgencia"
        )
        guardar_nota = st.form_submit_button("Guardar nota", type="primary")

        if guardar_nota:
            texto_limpio = texto_nota.strip()
            if not texto_limpio:
                st.warning("El texto de la nota no puede estar vacio.")
            else:
                add_nota_enfermeria(fecha_nota.isoformat(), texto_limpio, urgencia_sel)
                st.success("Nota de enfermería guardada.")
                st.rerun()

    df_notas_enf = get_notas_enfermeria()
    if df_notas_enf.empty:
        st.info("No hay notas de enfermería pendientes.")
    else:
        st.caption("Marca una nota como realizada para eliminarla automáticamente.")
        for _, row in df_notas_enf.iterrows():
            urg = str(row.get("urgencia") or "verde").strip().lower()
            if urg not in urgencias:
                urg = "verde"
            cfg_urg = urgencias[urg]

            fecha_txt = formatear_fecha_visita(row.get("fecha_nota"))
            latencia_txt = formatear_latencia_desde_creacion(row.get("creado_en"))

            st.markdown(
                f"{cfg_urg['icono']} **{cfg_urg['label']}** | Fecha nota: **{fecha_txt}** | "
                f"Latencia desde creación: **{latencia_txt}**"
            )
            st.markdown(
                f"<div style='border-left: 4px solid {cfg_urg['color']}; padding: 8px 12px; "
                f"background: #fff; border-radius: 4px;'>{html.escape(str(row.get('texto') or ''))}</div>",
                unsafe_allow_html=True
            )
            if st.button("✅ Marcar como realizado (borrar)", key=f"nota_enf_done_{int(row['id'])}"):
                latencia_cierre = formatear_latencia_desde_creacion(row.get("creado_en"))
                delete_nota_enfermeria(int(row["id"]))
                st.success(f"Nota realizada y eliminada. Latencia de respuesta: {latencia_cierre}.")
                st.rerun()
            st.markdown("---")

if seccion_activa == "Agenda":
    with st.expander("📌 Ver resumen de mañana", expanded=False):
        render_resumen_manana()

    col_cal, col_detalles = st.columns([2, 1])

    # 1. Preparar eventos para el calendario
    df_visitas = get_visitas()
    calendar_events = construir_eventos_calendario(df_visitas)

    # 2. Configuración del Calendario
    calendar_options = {
        "editable": True,
        "navLinks": True,
        "initialView": "dayGridMonth",
        "headerToolbar": {
            "left": "today prev,next",
            "center": "title",
            "right": "dayGridMonth,listDay"
        },
        "initialDate": fecha_hoy_local().isoformat(),
        "firstDay": 1,
        "selectable": True,
    }

    with col_cal:
        calendar_state = calendar(events=calendar_events, options=calendar_options, key="mi_calendario_v3")

    if calendar_state is None:
        calendar_state = {}

    # --- LÓGICA DE DETECCIÓN DE CLICS ---
    # Si se hace clic en el calendario, actualizamos la memoria (Session State)
    if calendar_state.get("dateClick"):
        st.session_state['modo_formulario'] = 'nuevo'
        st.session_state['datos_seleccionados'] = calendar_state["dateClick"].get("dateStr") or calendar_state["dateClick"]["date"]

    elif calendar_state.get("eventClick"):
        st.session_state['modo_formulario'] = 'ver'
        # Guardamos el ID del evento clickado
        props = calendar_state["eventClick"]["event"].get("extendedProps", {})
        if "id" in props:
            st.session_state['datos_seleccionados'] = props["id"]
        else:
            st.session_state['modo_formulario'] = None

    # --- PANEL LATERAL (DERECHA) ---
    with col_detalles:
        # MODO: NUEVO PACIENTE
        if st.session_state['modo_formulario'] == 'nuevo':
            fecha_activa = st.session_state['datos_seleccionados']
            st.subheader(f"📝 Nuevo Paciente: {fecha_activa}")

            df_pacientes = get_pacientes_unicos()
            opciones_pacientes = ["Nuevo paciente"]
            mapa_pacientes = {}
            if not df_pacientes.empty:
                for _, row in df_pacientes.iterrows():
                    codigo = "" if pd.isna(row['codigo']) else str(row['codigo'])
                    nombre = "" if pd.isna(row['nombre']) else str(row['nombre'])
                    ensayo = "" if pd.isna(row['ensayo']) else str(row['ensayo'])
                    etiqueta = f"{codigo} | {nombre} | {ensayo}".strip(" |")
                    opciones_pacientes.append(etiqueta)
                    mapa_pacientes[etiqueta] = {
                        "codigo": codigo,
                        "nombre": nombre,
                        "ensayo": ensayo
                    }

            seleccion = st.selectbox("Paciente guardado", opciones_pacientes)
            if seleccion != st.session_state['paciente_seleccionado']:
                st.session_state['paciente_seleccionado'] = seleccion
                if seleccion == "Nuevo paciente":
                    st.session_state['codigo_input'] = ""
                    st.session_state['nombre_input'] = ""
                    st.session_state['ensayo_input'] = ""
                else:
                    datos_sel = mapa_pacientes.get(seleccion, {})
                    st.session_state['codigo_input'] = datos_sel.get("codigo", "")
                    st.session_state['nombre_input'] = datos_sel.get("nombre", "")
                    st.session_state['ensayo_input'] = datos_sel.get("ensayo", "")

            with st.form("form_alta", clear_on_submit=True):
                c1, c2 = st.columns(2)
                nombre = c1.text_input("Nombre / Iniciales", key="nombre_input")
                codigo = c2.text_input("Código Sujeto (Obligatorio)", key="codigo_input")

                ensayos_existentes = get_ensayos_existentes()
                opcion_nuevo_ensayo = "➕ Añadir ensayo nuevo"
                opciones_ensayo = [opcion_nuevo_ensayo] + ensayos_existentes

                ensayo_previo = normalizar_ensayo(st.session_state.get("ensayo_input", ""))
                if ensayo_previo and ensayo_previo in ensayos_existentes:
                    indice_ensayo = opciones_ensayo.index(ensayo_previo)
                else:
                    indice_ensayo = 0

                ensayo_seleccionado = st.selectbox(
                    "Ensayo / Protocolo",
                    options=opciones_ensayo,
                    index=indice_ensayo,
                    key="ensayo_select_nuevo"
                )

                if ensayo_seleccionado == opcion_nuevo_ensayo:
                    ensayo = st.text_input("Nuevo ensayo / Protocolo", key="ensayo_input")
                else:
                    ensayo = ensayo_seleccionado
                    st.session_state["ensayo_input"] = ensayo_seleccionado

                ciclo = st.text_input("Ciclo / Día (Ej. C1D1)")

                st.divider()
                tab_medula, tab_kits, tab_otras, tab_comentarios = st.tabs(
                    ["Médula/Tablet", "Kits", "Otras pruebas", "Comentarios"]
                )
                with tab_medula:
                    cc1, cc2 = st.columns(2)
                    tablet = cc1.checkbox("Requiere Tablet")
                    medula = cc2.checkbox("🩸 Punción Médula")
                with tab_kits:
                    kits = st.text_input("Kits / Medicación")
                with tab_otras:
                    otras = st.text_area("Otras pruebas")
                with tab_comentarios:
                    notas = st.text_area("Comentarios")

                col_b1, col_b2 = st.columns(2)
                submitted = col_b1.form_submit_button("💾 Guardar", type="primary")

                if submitted:
                    if codigo:
                        datos = {
                            "nombre": nombre, "codigo": codigo, "ensayo": ensayo,
                            "ciclo": ciclo, "kits": kits, "tablet": tablet,
                            "medula": medula, "otras_pruebas": otras, "comentarios": notas
                        }
                        guardar_visita(fecha_activa, datos)
                        st.success("Guardado correctamente.")
                        # Reseteamos estado para limpiar
                        st.session_state['modo_formulario'] = None
                        st.rerun()
                    else:
                        st.error("¡Falta el Código del sujeto!")

            if st.button("Cancelar"):
                st.session_state['modo_formulario'] = None
                st.rerun()

        # MODO: VER DETALLES
        elif st.session_state['modo_formulario'] == 'ver':
            id_evento = st.session_state['datos_seleccionados']

            # Buscamos el paciente en la DB
            df_visitas_view = get_visitas()
            if df_visitas_view.empty:
                st.warning("No se encontraron datos (quizás se borró).")
                if st.button("Volver"):
                    st.session_state['modo_formulario'] = None
                    st.rerun()
            else:
                try:
                    id_evento_cmp = int(id_evento)
                except (TypeError, ValueError):
                    id_evento_cmp = id_evento

                df_filtrado = df_visitas_view[df_visitas_view['id'] == id_evento_cmp]

                if not df_filtrado.empty:
                    paciente = df_filtrado.iloc[0]

                    fecha_visita = formatear_fecha_visita(paciente['fecha'])
                    st.info(f"📅 Fecha de visita: {fecha_visita}")
                    st.markdown(f"## 🆔 {paciente['codigo']}")
                    st.markdown(f"**Paciente:** {paciente['nombre']}")
                    st.markdown(f"**Ensayo:** {paciente['ensayo']} | **Ciclo:** {paciente['ciclo']}")

                    st.divider()
                    with st.expander("Editar visita"):
                        fecha_default = parse_fecha_iso(paciente['fecha']) or fecha_hoy_local()
                        with st.form(f"form_editar_{id_evento_cmp}"):
                            c1, c2 = st.columns(2)
                            nombre_edit = c1.text_input(
                                "Nombre / Iniciales",
                                value=paciente['nombre'] or ""
                            )
                            codigo_edit = c2.text_input(
                                "Código Sujeto (Obligatorio)",
                                value=paciente['codigo'] or ""
                            )
                            ensayo_edit = st.text_input(
                                "Ensayo / Protocolo",
                                value=paciente['ensayo'] or ""
                            )
                            fecha_edit = st.date_input("Fecha de visita", value=fecha_default)
                            ciclo_edit = st.text_input(
                                "Ciclo / Día (Ej. C1D1)",
                                value=paciente['ciclo'] or ""
                            )
                            st.divider()
                            tab_medula_e, tab_kits_e, tab_otras_e, tab_comentarios_e = st.tabs(
                                ["Médula/Tablet", "Kits", "Otras pruebas", "Comentarios"]
                            )
                            with tab_medula_e:
                                cc1, cc2 = st.columns(2)
                                tablet_edit = cc1.checkbox(
                                    "Requiere Tablet",
                                    value=bool(paciente['tablet'])
                                )
                                medula_edit = cc2.checkbox(
                                    "🩸 Punción Médula",
                                    value=bool(paciente['medula'])
                                )
                            with tab_kits_e:
                                kits_edit = st.text_input(
                                    "Kits / Medicación",
                                    value=paciente['kits'] or ""
                                )
                            with tab_otras_e:
                                otras_edit = st.text_area(
                                    "Otras pruebas",
                                    value=paciente['otras_pruebas'] or ""
                                )
                            with tab_comentarios_e:
                                notas_edit = st.text_area(
                                    "Comentarios",
                                    value=paciente['comentarios'] or ""
                                )

                            guardar_edicion = st.form_submit_button("Guardar cambios", type="primary")
                            if guardar_edicion:
                                if codigo_edit:
                                    datos_edit = {
                                        "nombre": nombre_edit,
                                        "codigo": codigo_edit,
                                        "ensayo": ensayo_edit,
                                        "ciclo": ciclo_edit,
                                        "kits": kits_edit,
                                        "tablet": tablet_edit,
                                        "medula": medula_edit,
                                        "otras_pruebas": otras_edit,
                                        "comentarios": notas_edit
                                    }
                                    actualizar_visita(
                                        id_evento_cmp,
                                        fecha_edit.isoformat(),
                                        datos_edit
                                    )
                                    st.success("Visita actualizada correctamente.")
                                    st.rerun()
                                else:
                                    st.error("¡Falta el Código del sujeto!")

                    st.divider()
                    tab_medula, tab_kits, tab_otras, tab_comentarios = st.tabs(
                        ["Médula/Tablet", "Kits", "Otras pruebas", "Comentarios"]
                    )
                    with tab_medula:
                        if paciente['medula']:
                            st.error("🩸 **Requiere Médula Ósea**")
                        else:
                            st.success("Sin punción de médula")
                        if paciente['tablet']:
                            st.warning("📱 **Preparar Tablet**")
                        else:
                            st.info("Sin tablet")
                    with tab_kits:
                        st.write(paciente['kits'] if paciente['kits'] else "Sin datos")
                    with tab_otras:
                        st.write(paciente['otras_pruebas'] if paciente['otras_pruebas'] else "Sin datos")
                    with tab_comentarios:
                        st.write(paciente['comentarios'] if paciente['comentarios'] else "Sin datos")

                    st.divider()
                    st.subheader("Revision ocular")
                    rev = get_revision_ocular(id_evento_cmp)
                    tiene_rev = bool(rev and (rev[0] or rev[1] is not None))
                    opcion_rev = st.radio(
                        "Revision ocular",
                        options=["No", "Si"],
                        index=1 if tiene_rev else 0,
                        horizontal=True,
                        key=f"revision_ocular_{id_evento_cmp}"
                    )

                    if opcion_rev == "Si":
                        fecha_default = parse_fecha_iso(rev[0]) if rev else None
                        if fecha_default is None:
                            fecha_default = parse_fecha_iso(paciente['fecha']) or fecha_hoy_local()
                        kva_default = rev[1] if rev and rev[1] is not None else 0
                        kva_opciones = [0, 1, 2, 3, 4]
                        kva_index = kva_opciones.index(kva_default) if kva_default in kva_opciones else 0

                        with st.form(f"form_revision_{id_evento_cmp}"):
                            fecha_cita = st.date_input("Fecha de cita", value=fecha_default)
                            kva = st.selectbox("Resultado KVA", options=kva_opciones, index=kva_index)
                            guardar_rev = st.form_submit_button("Guardar revision ocular")
                            if guardar_rev:
                                guardar_revision_ocular(id_evento_cmp, fecha_cita.isoformat(), kva)
                                st.success("Revision ocular guardada.")

                    informe = (
                        f"Informe de visita\n"
                        f"Fecha: {fecha_visita}\n"
                        f"Codigo: {paciente['codigo']}\n"
                        f"Paciente: {paciente['nombre']}\n"
                        f"Ensayo: {paciente['ensayo']}\n"
                        f"Ciclo: {paciente['ciclo']}\n"
                        f"Kits: {paciente['kits']}\n"
                        f"Tablet: {'Si' if paciente['tablet'] else 'No'}\n"
                        f"Medula: {'Si' if paciente['medula'] else 'No'}\n"
                        f"Otras pruebas: {paciente['otras_pruebas']}\n"
                        f"Comentarios: {paciente['comentarios']}\n"
                    )
                    st.download_button(
                        "Descargar informe",
                        data=informe,
                        file_name=f"informe_{paciente['codigo']}_{fecha_visita}.txt",
                        mime="text/plain"
                    )
                    if st.button("Imprimir informe"):
                        titulo = f"Informe {paciente['codigo']} - {fecha_visita}"
                        render_print_dialog(informe, titulo)

                    st.divider()
                    col_del, col_close = st.columns(2)
                    if col_del.button("🗑️ Borrar Cita", type="primary"):
                        borrar_visita(id_evento)
                        st.session_state['modo_formulario'] = None
                        st.rerun()

                    if col_close.button("Cerrar Ficha"):
                        st.session_state['modo_formulario'] = None
                        st.rerun()
                else:
                    st.warning("No se encontraron datos (quizás se borró).")
                    if st.button("Volver"):
                        st.session_state['modo_formulario'] = None
                        st.rerun()

        else:
            st.info("👈 Haz clic en un día para añadir pacientes.")
            st.caption("Los días con '🩸' indican punción de médula.")
