import streamlit as st
try:
    from streamlit_calendar import calendar
except ImportError:
    calendar = None
import sqlite3
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import html
import streamlit.components.v1 as components
import os
import re
import base64
import io
import json
import shutil
import zipfile
import hashlib
import hmac
import webbrowser
import tempfile
import importlib
import glob
import runpy
from urllib.parse import quote_plus

try:
    from PIL import Image
except ImportError:
    Image = None

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

# Icono para la pestaña del navegador (disponible antes de set_page_config).
BOOT_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BOOT_LOGO_CANDIDATOS = [
    os.path.join(BOOT_SCRIPT_DIR, "favicon.ico"),
    os.path.join(BOOT_SCRIPT_DIR, "cabuenes_corregido.png"),
    os.path.join(BOOT_SCRIPT_DIR, "ChatGPT Image 10 mar 2026, 09_32_03.png"),
    os.path.join(BOOT_SCRIPT_DIR, "ChatGPT Image 10 mar 2026, 09_22_55.png"),
]
BOOT_PAGE_ICON = ""
for _ruta_logo in BOOT_LOGO_CANDIDATOS:
    if os.path.isfile(_ruta_logo):
        if Image is not None:
            try:
                BOOT_PAGE_ICON = Image.open(_ruta_logo)
            except Exception:
                BOOT_PAGE_ICON = _ruta_logo
        else:
            BOOT_PAGE_ICON = _ruta_logo
        break

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Agenda Ensayos Clinicos 2026",
    page_icon=BOOT_PAGE_ICON if BOOT_PAGE_ICON else "🩺",
    layout="wide",
)

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
                width: 360px !important;
            }}
            section[data-testid="stSidebar"] > div {{
                width: 360px !important;
                background: rgba(234, 244, 255, 0.9) !important;
                padding-top: 0.4rem !important;
                padding-left: 0.45rem !important;
                padding-right: 0.45rem !important;
            }}
            section[data-testid="stSidebar"] .sidebar-logo-frame {{
                height: 130px !important;
                width: 100% !important;
                max-width: 100% !important;
                overflow: hidden !important;
                background: transparent !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                margin: 0 0 0.45rem 0 !important;
                padding: 0 !important;
                box-sizing: border-box !important;
                border: none !important;
                box-shadow: none !important;
            }}
            section[data-testid="stSidebar"] .sidebar-logo-frame img {{
                width: 100% !important;
                max-width: 100% !important;
                height: auto !important;
                display: block !important;
                transform: scale(1.6) !important;
                transform-origin: center center !important;
                border-radius: 0 !important;
                box-shadow: none !important;
            }}
            section[data-testid="stSidebar"] label[data-testid="stWidgetLabel"] p {{
                font-size: 1.1rem !important;
                font-weight: 700 !important;
            }}
            section[data-testid="stSidebar"] div[role="radiogroup"] label p {{
                font-size: 1.02rem !important;
                font-weight: 600 !important;
                line-height: 1.35 !important;
            }}
            @media (max-width: 900px) {{
                section[data-testid="stSidebar"],
                section[data-testid="stSidebar"] > div {{
                    width: 260px !important;
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
                gap: 0.6rem;
                margin-bottom: 0.7rem;
            }}
            button[data-baseweb="tab"] {{
                white-space: normal;
                height: auto;
                min-height: 2.6rem;
                padding: 0.45rem 0.85rem !important;
                border-radius: 10px !important;
                border: 1px solid #bfdbfe !important;
                background: #eff6ff !important;
                font-size: 0.98rem !important;
                font-weight: 600 !important;
            }}
            button[data-baseweb="tab"][aria-selected="true"] {{
                background: #dbeafe !important;
                border-color: #60a5fa !important;
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
DREAMM10_XLSX_DIR = os.path.join(SCRIPT_DIR, "DREAMM10 calendario pacientes")
CHECKLIST_GLOBAL_XLSX = os.path.join(SCRIPT_DIR, "checklist_todos_los_ensayos.xlsx")
APP_TIMEZONE = "Europe/Madrid"
DB_PATH = os.path.join(SCRIPT_DIR, "agenda_ensayos.db")
DB_BACKUP_DIR = os.path.join(SCRIPT_DIR, "backups_db")
BACKUP_ENSAYOS_DIR = r"H:\ENSAYOS\ENSAYOS\BASE DE DATOS APP ENSAYOS"
APP_BUILD = datetime.fromtimestamp(os.path.getmtime(__file__)).strftime("%Y-%m-%d %H:%M")
LOGO_PATH = resolver_archivo(
    os.path.join(SCRIPT_DIR, "cabuenes_corregido.png"),
    os.path.join(SCRIPT_DIR, "ChatGPT Image 10 mar 2026, 09_32_03.png"),
    os.path.join(SCRIPT_DIR, "ChatGPT Image 10 mar 2026, 09_22_55.png")
)


def aplicar_marca_pestana(titulo_objetivo, ruta_logo):
    if not ruta_logo or not os.path.isfile(ruta_logo):
        return
    try:
        if Image is not None:
            imagen_base = Image.open(ruta_logo).convert("RGBA")

            def _a_data_url(tamano: tuple[int, int]) -> str:
                imagen = imagen_base.copy()
                imagen.thumbnail(tamano, Image.Resampling.LANCZOS)
                lienzo = Image.new("RGBA", tamano, (0, 0, 0, 0))
                offset = ((tamano[0] - imagen.width) // 2, (tamano[1] - imagen.height) // 2)
                lienzo.paste(imagen, offset, imagen)
                buffer = io.BytesIO()
                lienzo.save(buffer, format="PNG")
                return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("utf-8")

            icono_32 = _a_data_url((32, 32))
            icono_180 = _a_data_url((180, 180))
            icono_192 = _a_data_url((192, 192))
            icono_512 = _a_data_url((512, 512))
        else:
            with open(ruta_logo, "rb") as f_logo:
                icono_b64 = base64.b64encode(f_logo.read()).decode("utf-8")
            icono_32 = f"data:image/png;base64,{icono_b64}"
            icono_180 = icono_32
            icono_192 = icono_32
            icono_512 = icono_32
    except Exception:
        return

    components.html(
        f"""
        <script>
            const tituloObjetivo = {titulo_objetivo!r};
            const iconoFavicon = {icono_32!r};
            const iconoApple = {icono_180!r};
            const icono192 = {icono_192!r};
            const icono512 = {icono_512!r};
            const manifestData = {{
                name: tituloObjetivo,
                short_name: tituloObjetivo,
                start_url: ".",
                scope: ".",
                display: "standalone",
                background_color: "#dbeafe",
                theme_color: "#dbeafe",
                icons: [
                    {{ src: icono192, sizes: "192x192", type: "image/png" }},
                    {{ src: icono512, sizes: "512x512", type: "image/png" }},
                ],
            }};
            const manifestHref = "data:application/manifest+json;charset=utf-8," + encodeURIComponent(JSON.stringify(manifestData));

            function aplicarMarca() {{
                try {{
                    const doc = (window.parent && window.parent.document) ? window.parent.document : document;
                    if (doc.title !== tituloObjetivo) {{
                        doc.title = tituloObjetivo;
                    }}

                    const metaMobile = [
                        {{ name: "apple-mobile-web-app-capable", content: "yes" }},
                        {{ name: "apple-mobile-web-app-title", content: tituloObjetivo }},
                        {{ name: "mobile-web-app-capable", content: "yes" }},
                        {{ name: "theme-color", content: "#dbeafe" }},
                    ];
                    metaMobile.forEach((item) => {{
                        const name = item.name;
                        const content = item.content;
                        let meta = doc.querySelector(`meta[name='${{name}}']`);
                        if (!meta) {{
                            meta = doc.createElement("meta");
                            meta.setAttribute("name", name);
                            doc.head.appendChild(meta);
                        }}
                        if (meta.getAttribute("content") !== content) {{
                            meta.setAttribute("content", content);
                        }}
                    }});

                    const iconos = [
                        {{ rel: "icon", href: iconoFavicon, sizes: "32x32", type: "image/png" }},
                        {{ rel: "icon", href: icono192, sizes: "192x192", type: "image/png" }},
                        {{ rel: "icon", href: icono512, sizes: "512x512", type: "image/png" }},
                        {{ rel: "shortcut icon", href: iconoFavicon, sizes: "32x32", type: "image/png" }},
                        {{ rel: "apple-touch-icon", href: iconoApple, sizes: "180x180", type: "image/png" }},
                        {{ rel: "apple-touch-icon-precomposed", href: iconoApple, sizes: "180x180", type: "image/png" }},
                        {{ rel: "manifest", href: manifestHref, type: "application/manifest+json" }},
                    ];

                    iconos.forEach(({{ rel, href, sizes, type }}) => {{
                        let icono = doc.querySelector(`link[rel='${{rel}}']`);
                        if (!icono) {{
                            icono = doc.createElement("link");
                            icono.setAttribute("rel", rel);
                            doc.head.appendChild(icono);
                        }}
                        if (sizes) {{
                            icono.setAttribute("sizes", sizes);
                        }}
                        if (type) {{
                            icono.setAttribute("type", type);
                        }}
                        if (icono.getAttribute("href") !== href) {{
                            icono.setAttribute("href", href);
                        }}
                    }});
                }} catch (e) {{}}
            }}

            aplicarMarca();
            setTimeout(aplicarMarca, 300);
            setTimeout(aplicarMarca, 1200);
            setTimeout(aplicarMarca, 3000);
        </script>
        """,
        height=0,
    )


aplicar_marca_pestana("Agenda Ensayos Clinicos 2026", LOGO_PATH)


def renderizar_logo_sidebar(ruta_logo):
    if not ruta_logo or not os.path.isfile(ruta_logo):
        st.sidebar.caption("Logo no encontrado")
        return

    try:
        with open(ruta_logo, "rb") as f_logo:
            logo_b64 = base64.b64encode(f_logo.read()).decode("utf-8")
    except OSError:
        st.sidebar.caption("Logo no encontrado")
        return

    st.sidebar.markdown(
        f"""
        <div class="sidebar-logo-frame">
            <img src="data:image/png;base64,{logo_b64}" alt="Logo Hematologia" />
        </div>
        """,
        unsafe_allow_html=True,
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


def _auth_configurada():
    pwd_hash = str(leer_config("APP_PASSWORD_HASH_SHA256", "")).strip().lower()
    pwd_plano = str(leer_config("APP_PASSWORD", "")).strip()
    pwd_hash_fallback = "c1a96bdc66e356a5d4edf39ba4a4ebc365013fc29ea990f53148d86be74c33ad"  # Ensayos*
    return bool(pwd_hash or pwd_plano or pwd_hash_fallback)


def _validar_password(password_ingresada):
    pwd_hash = str(leer_config("APP_PASSWORD_HASH_SHA256", "")).strip().lower()
    pwd_plano = str(leer_config("APP_PASSWORD", "")).strip()
    pwd_hash_fallback = "c1a96bdc66e356a5d4edf39ba4a4ebc365013fc29ea990f53148d86be74c33ad"  # Ensayos*

    if not password_ingresada:
        return False

    if not pwd_hash and not pwd_plano:
        pwd_hash = pwd_hash_fallback

    if pwd_hash:
        hash_ingresado = hashlib.sha256(password_ingresada.encode("utf-8")).hexdigest().lower()
        return hmac.compare_digest(hash_ingresado, pwd_hash)

    if pwd_plano:
        return hmac.compare_digest(password_ingresada, pwd_plano)

    return True


def requerir_login_si_configurado():
    if not _auth_configurada():
        return

    if st.session_state.get("_auth_ok", False):
        return

    st.title("🔒 Acceso a la aplicación")
    st.caption("Introduce la contraseña para continuar")

    with st.form("form_login_app", clear_on_submit=False):
        password = st.text_input("Contraseña", type="password")
        enviar = st.form_submit_button("Entrar")

    if enviar:
        if _validar_password(password):
            st.session_state["_auth_ok"] = True
            st.session_state.pop("_auth_error", None)
            st.rerun()
        else:
            st.session_state["_auth_error"] = "Contraseña incorrecta"

    if st.session_state.get("_auth_error"):
        st.error(st.session_state["_auth_error"])

    st.stop()


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


def resolver_carpeta_backup_diario():
    candidatos = []

    ruta_configurada = str(leer_config("BACKUP_ENSAYOS_DIR", BACKUP_ENSAYOS_DIR)).strip()
    if ruta_configurada:
        candidatos.append(ruta_configurada)

    # Si viene una ruta Windows (H:\...), en Linux intentamos rutas montadas equivalentes.
    m_drive = re.match(r"^([A-Za-z]):\\(.+)$", ruta_configurada)
    if os.name != "nt" and m_drive:
        drive = m_drive.group(1).lower()
        resto = m_drive.group(2).replace("\\", "/")
        candidatos.extend(
            [
                f"/mnt/{drive}/{resto}",
                f"/media/{m_drive.group(1).upper()}/{resto}",
            ]
        )

    candidatos.append(DB_BACKUP_DIR)

    for carpeta in candidatos:
        if not carpeta:
            continue
        # En Linux/macOS, una ruta tipo H:\... no es una unidad real montada.
        if os.name != "nt" and re.match(r"^[A-Za-z]:\\", carpeta):
            continue
        try:
            os.makedirs(carpeta, exist_ok=True)
            return carpeta
        except OSError:
            continue
    return ""


def backup_diario_ensayos(forzar=False):
    """Exporta una copia diaria de todas las tablas a BACKUP_ENSAYOS_DIR.

    - SQLite  → copia el archivo .db con fecha en el nombre.
    - PostgreSQL → exporta cada tabla como CSV en una subcarpeta con fecha.
    La carpeta destino solo existe en el equipo local; si no es accesible
    (modo cloud) la función termina silenciosamente.
    Se conservan los 60 últimos backups diarios.
    """
    carpeta = resolver_carpeta_backup_diario()
    if not carpeta:
        return False, ""

    ahora = datetime.now()
    hoy = ahora.strftime("%Y%m%d")

    if DB_BACKEND == "sqlite":
        if not os.path.exists(DB_PATH):
            return False, carpeta
        destino = os.path.join(carpeta, f"agenda_ensayos_{hoy}.db")
        if os.path.exists(destino) and not forzar:
            return True, carpeta  # Ya se hizo el backup de hoy
        if forzar:
            destino = os.path.join(carpeta, f"agenda_ensayos_{ahora.strftime('%Y%m%d_%H%M%S')}.db")
        try:
            src = connect_db()
            dst = sqlite3.connect(destino)
            try:
                src.backup(dst)
            finally:
                dst.close()
                src.close()
        except Exception:
            return False, carpeta
        # Mantener solo los 60 más recientes
        try:
            archivos = sorted(
                [f for f in os.listdir(carpeta)
                 if f.startswith("agenda_ensayos_") and f.endswith(".db")],
                reverse=True,
            )
            for viejo in archivos[60:]:
                try:
                    os.remove(os.path.join(carpeta, viejo))
                except OSError:
                    pass
        except OSError:
            pass
        return True, carpeta
    else:
        # PostgreSQL: exportar cada tabla a CSV
        tablas = [
            "visitas", "revision_ocular", "pacientes", "checklist_items",
            "notas_esquemas", "notas_enfermeria", "notas_coordinacion",
            "adendas_ensayo", "adendas_paciente", "dreamm10_excels",
        ]
        subcarpeta = os.path.join(carpeta, f"backup_{hoy}")
        marca = os.path.join(subcarpeta, ".completado")
        if os.path.exists(marca) and not forzar:
            return True, carpeta  # Ya se hizo el backup de hoy
        if forzar:
            subcarpeta = os.path.join(carpeta, f"backup_{ahora.strftime('%Y%m%d_%H%M%S')}")
            marca = os.path.join(subcarpeta, ".completado")
        try:
            os.makedirs(subcarpeta, exist_ok=True)
            conn = connect_db()
            try:
                for tabla in tablas:
                    try:
                        df = pd.read_sql_query(f"SELECT * FROM {tabla}", conn)  # noqa: S608
                        df.to_csv(
                            os.path.join(subcarpeta, f"{tabla}.csv"),
                            index=False,
                            encoding="utf-8-sig",
                        )
                    except Exception:
                        pass
            finally:
                conn.close()
            with open(marca, "w", encoding="utf-8") as _m:
                _m.write(datetime.now().isoformat())
        except Exception:
            return False, carpeta
        # Mantener solo los 60 más recientes
        try:
            subcarpetas = sorted(
                [f for f in os.listdir(carpeta)
                 if f.startswith("backup_") and os.path.isdir(os.path.join(carpeta, f))],
                reverse=True,
            )
            for vieja in subcarpetas[60:]:
                shutil.rmtree(os.path.join(carpeta, vieja), ignore_errors=True)
        except OSError:
            pass
        return True, carpeta


def existe_backup_diario_hoy(carpeta):
    if not carpeta:
        return False
    hoy = datetime.now().strftime("%Y%m%d")
    if DB_BACKEND == "sqlite":
        return os.path.exists(os.path.join(carpeta, f"agenda_ensayos_{hoy}.db"))
    return os.path.exists(os.path.join(carpeta, f"backup_{hoy}", ".completado"))


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


def construir_backup_descargable():
    ahora = datetime.now()

    if DB_BACKEND == "sqlite":
        db_bytes = export_db_bytes()
        if not db_bytes:
            return None, "", ""
        nombre = f"agenda_ensayos_{ahora.strftime('%Y%m%d_%H%M%S')}.db"
        return db_bytes, nombre, "application/octet-stream"

    tablas = [
        "visitas", "revision_ocular", "pacientes", "checklist_items",
        "notas_esquemas", "notas_enfermeria", "notas_coordinacion",
        "adendas_ensayo", "adendas_paciente", "dreamm10_excels",
    ]

    buffer = io.BytesIO()
    conn = connect_db()
    try:
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for tabla in tablas:
                try:
                    df = pd.read_sql_query(f"SELECT * FROM {tabla}", conn)  # noqa: S608
                    zf.writestr(f"{tabla}.csv", df.to_csv(index=False, encoding="utf-8-sig"))
                except Exception:
                    continue
            zf.writestr(
                "_meta.txt",
                (
                    "Backup exportado desde Agenda Ensayos Clinicos\n"
                    f"Fecha: {ahora.isoformat()}\n"
                    f"Backend: {DB_BACKEND}\n"
                ),
            )
    except Exception:
        return None, "", ""
    finally:
        conn.close()

    nombre = f"agenda_ensayos_{ahora.strftime('%Y%m%d_%H%M%S')}.zip"
    return buffer.getvalue(), nombre, "application/zip"


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

    if clave == "DREAMM10":
        return "DREAMM 10"
    if clave == "DREAMM8":
        return "DREAMM-8"
    if clave == "FUERADEENSAYO":
        return "Fuera de Ensayo"

    if clave in {"GEM21", "GEM2021"}:
        return "GEM21"

    match_rgn = re.fullmatch(r"RGN[\s\-_/]*([0-9]+)", ensayo)
    if match_rgn:
        return match_rgn.group(1)
    return ensayo


def es_ensayo_dreamm10(valor):
    ensayo_norm = normalizar_ensayo(valor)
    clave = re.sub(r"[\s\-_/]+", "", ensayo_norm)
    return clave == "DREAMM10"


def es_visita_importada_dreamm10(ensayo, comentarios):
    if not es_ensayo_dreamm10(ensayo):
        return False

    comentario_norm = normalizar_texto_campo(comentarios).lower()
    marcadores = (
        "paciente (pestaña):",
        "paciente (pestana):",
        "importado desde excel dreamm10",
    )
    return any(marcador in comentario_norm for marcador in marcadores)


def filtrar_visitas_importadas_dreamm10(df):
    if df is None or df.empty or "ensayo" not in df.columns:
        return df
    if "comentarios" not in df.columns:
        return df

    mask = ~df.apply(
        lambda row: es_visita_importada_dreamm10(
            row.get("ensayo", ""),
            row.get("comentarios", ""),
        ),
        axis=1,
    )
    return df[mask].copy()


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


def _obtener_columnas_tabla(cursor, tabla: str) -> set[str]:
    tabla_limpia = str(tabla or "").strip()
    if not tabla_limpia:
        return set()

    try:
        if DB_BACKEND == "postgres":
            filas = cursor.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = ?
                """,
                (tabla_limpia,),
            ).fetchall()
            return {str(f[0]).strip().lower() for f in filas if f and f[0] is not None}

        filas = cursor.execute(f"PRAGMA table_info({tabla_limpia})").fetchall()
        return {str(f[1]).strip().lower() for f in filas if len(f) > 1 and f[1] is not None}
    except Exception:
        return set()


def _resolver_columna_nombre(cursor, tabla: str) -> str | None:
    columnas = _obtener_columnas_tabla(cursor, tabla)
    candidatos = ["nombre", "nombre_paciente", "paciente", "iniciales"]
    for cand in candidatos:
        if cand in columnas:
            return cand
    return None


def _resolver_columna_ensayo(cursor, tabla: str) -> str | None:
    columnas = _obtener_columnas_tabla(cursor, tabla)
    candidatos = ["ensayo", "estudio", "protocolo", "trial"]
    for cand in candidatos:
        if cand in columnas:
            return cand
    return None


def normalizar_ensayos_existentes(cursor):
    col_ensayo_visitas = _resolver_columna_ensayo(cursor, "visitas")
    if col_ensayo_visitas:
        visitas = cursor.execute(
            f"SELECT id, {col_ensayo_visitas} FROM visitas"
        ).fetchall()
        for visita_id, ensayo in visitas:
            ensayo_norm = normalizar_ensayo(ensayo)
            if ensayo_norm != ("" if ensayo is None else str(ensayo)):
                cursor.execute(
                    f"UPDATE visitas SET {col_ensayo_visitas} = ? WHERE id = ?",
                    (ensayo_norm, visita_id)
                )

    col_ensayo_checklist = _resolver_columna_ensayo(cursor, "checklist_items")
    if col_ensayo_checklist:
        checklist = cursor.execute(
            f"SELECT id, {col_ensayo_checklist} FROM checklist_items"
        ).fetchall()
        for item_id, ensayo in checklist:
            ensayo_norm = normalizar_ensayo(ensayo)
            if ensayo_norm != ("" if ensayo is None else str(ensayo)):
                cursor.execute(
                    f"UPDATE checklist_items SET {col_ensayo_checklist} = ? WHERE id = ?",
                    (ensayo_norm, item_id)
                )


def anonimizar_nombres_existentes(cursor):
    col_nombre_visitas = _resolver_columna_nombre(cursor, "visitas")
    if col_nombre_visitas:
        visitas = cursor.execute(
            f"SELECT id, {col_nombre_visitas} FROM visitas"
        ).fetchall()
        for visita_id, nombre in visitas:
            nombre_norm = nombre_a_iniciales(nombre)
            nombre_actual = "" if nombre is None else str(nombre)
            if nombre_norm != nombre_actual:
                cursor.execute(
                    f"UPDATE visitas SET {col_nombre_visitas} = ? WHERE id = ?",
                    (nombre_norm, visita_id)
                )

    col_nombre_pacientes = _resolver_columna_nombre(cursor, "pacientes")
    if col_nombre_pacientes:
        pacientes = cursor.execute(
            f"SELECT id, {col_nombre_pacientes} FROM pacientes"
        ).fetchall()
        for paciente_id, nombre in pacientes:
            nombre_norm = nombre_a_iniciales(nombre)
            nombre_actual = "" if nombre is None else str(nombre)
            if nombre_norm != nombre_actual:
                cursor.execute(
                    f"UPDATE pacientes SET {col_nombre_pacientes} = ? WHERE id = ?",
                    (nombre_norm, paciente_id)
                )


def eliminar_ensayos_sin_pacientes(cursor):
    col_nombre_pac = _resolver_columna_nombre(cursor, "pacientes") or "nombre"
    col_ensayo_pac = _resolver_columna_ensayo(cursor, "pacientes") or "ensayo"

    filas_pacientes = cursor.execute(
        f"SELECT codigo, {col_nombre_pac}, {col_ensayo_pac} FROM pacientes"
    ).fetchall()
    ensayos_validos = set()
    for codigo, nombre, ensayo in filas_pacientes:
        codigo_norm = normalizar_clave_paciente(codigo)
        nombre_norm = normalizar_clave_paciente(nombre)
        ensayo_norm = normalizar_clave_paciente(ensayo)
        if ensayo_norm and (codigo_norm or nombre_norm):
            ensayos_validos.add(ensayo_norm)

    col_ensayo_checklist = _resolver_columna_ensayo(cursor, "checklist_items")
    if not col_ensayo_checklist:
        return

    filas_checklist = cursor.execute(
        f"SELECT id, {col_ensayo_checklist} FROM checklist_items"
    ).fetchall()
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
                kva INTEGER,
                sede TEXT,
                medico TEXT,
                agenda_hospitalaria TEXT,
                fecha_evaluacion TEXT,
                resultado TEXT
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
        c.execute(
            '''
            CREATE TABLE IF NOT EXISTS notas_coordinacion (
                id BIGSERIAL PRIMARY KEY,
                fecha_nota TEXT NOT NULL,
                texto TEXT NOT NULL,
                urgencia TEXT NOT NULL,
                creado_en TEXT NOT NULL
            )
            '''
        )
        c.execute(
            '''
            CREATE TABLE IF NOT EXISTS adendas_ensayo (
                id BIGSERIAL PRIMARY KEY,
                ensayo TEXT UNIQUE,
                texto TEXT,
                fecha_modificacion TEXT
            )
            '''
        )
        c.execute(
            '''
            CREATE TABLE IF NOT EXISTS adendas_paciente (
                id BIGSERIAL PRIMARY KEY,
                clave_paciente TEXT UNIQUE,
                codigo TEXT,
                nombre TEXT,
                ensayo TEXT,
                texto TEXT,
                fecha_modificacion TEXT
            )
            '''
        )
        c.execute(
            '''
            CREATE TABLE IF NOT EXISTS dreamm10_excels (
                id BIGSERIAL PRIMARY KEY,
                nombre_archivo TEXT UNIQUE,
                contenido BYTEA,
                actualizado_en TEXT
            )
            '''
        )
        c.execute(
            '''
            CREATE TABLE IF NOT EXISTS interfaz_medica_visita (
                id BIGSERIAL PRIMARY KEY,
                visita_id BIGINT UNIQUE,
                estado_constantes TEXT,
                estado_comentarios TEXT,
                estado_pruebas TEXT,
                estado_farmacos_estudio TEXT,
                estado_medicacion_concomitante TEXT,
                estado_aes TEXT,
                estado_decision TEXT,
                nota_clinica TEXT,
                ultima_actualizacion TEXT
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
                sede TEXT,
                medico TEXT,
                agenda_hospitalaria TEXT,
                fecha_evaluacion TEXT,
                fechas_previas TEXT,
                resultado TEXT,
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
        c.execute('''
            CREATE TABLE IF NOT EXISTS notas_coordinacion (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha_nota TEXT NOT NULL,
                texto TEXT NOT NULL,
                urgencia TEXT NOT NULL,
                creado_en TEXT NOT NULL
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS adendas_ensayo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ensayo TEXT UNIQUE,
                texto TEXT,
                fecha_modificacion TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS adendas_paciente (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                clave_paciente TEXT UNIQUE,
                codigo TEXT,
                nombre TEXT,
                ensayo TEXT,
                texto TEXT,
                fecha_modificacion TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS dreamm10_excels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre_archivo TEXT UNIQUE,
                contenido BLOB,
                actualizado_en TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS interfaz_medica_visita (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                visita_id INTEGER UNIQUE,
                estado_constantes TEXT,
                estado_comentarios TEXT,
                estado_pruebas TEXT,
                estado_farmacos_estudio TEXT,
                estado_medicacion_concomitante TEXT,
                estado_aes TEXT,
                estado_decision TEXT,
                nota_clinica TEXT,
                ultima_actualizacion TEXT,
                FOREIGN KEY(visita_id) REFERENCES visitas(id)
            )
        ''')

    # Migracion incremental de revision ocular para instalaciones existentes.
    if DB_BACKEND == "postgres":
        c.execute("ALTER TABLE visitas ADD COLUMN IF NOT EXISTS nombre TEXT")
        c.execute("ALTER TABLE visitas ADD COLUMN IF NOT EXISTS codigo TEXT")
        c.execute("ALTER TABLE visitas ADD COLUMN IF NOT EXISTS ensayo TEXT")
        c.execute("ALTER TABLE pacientes ADD COLUMN IF NOT EXISTS nombre TEXT")
        c.execute("ALTER TABLE pacientes ADD COLUMN IF NOT EXISTS codigo TEXT")
        c.execute("ALTER TABLE pacientes ADD COLUMN IF NOT EXISTS ensayo TEXT")
        c.execute("ALTER TABLE checklist_items ADD COLUMN IF NOT EXISTS ensayo TEXT")
        c.execute("ALTER TABLE revision_ocular ADD COLUMN IF NOT EXISTS sede TEXT")
        c.execute("ALTER TABLE revision_ocular ADD COLUMN IF NOT EXISTS medico TEXT")
        c.execute("ALTER TABLE revision_ocular ADD COLUMN IF NOT EXISTS agenda_hospitalaria TEXT")
        c.execute("ALTER TABLE revision_ocular ADD COLUMN IF NOT EXISTS fecha_evaluacion TEXT")
        c.execute("ALTER TABLE revision_ocular ADD COLUMN IF NOT EXISTS fechas_previas TEXT")
        c.execute("ALTER TABLE revision_ocular ADD COLUMN IF NOT EXISTS resultado TEXT")
        c.execute("ALTER TABLE interfaz_medica_visita ADD COLUMN IF NOT EXISTS estado_constantes TEXT")
        c.execute("ALTER TABLE interfaz_medica_visita ADD COLUMN IF NOT EXISTS estado_comentarios TEXT")
        c.execute("ALTER TABLE interfaz_medica_visita ADD COLUMN IF NOT EXISTS estado_pruebas TEXT")
        c.execute("ALTER TABLE interfaz_medica_visita ADD COLUMN IF NOT EXISTS estado_farmacos_estudio TEXT")
        c.execute("ALTER TABLE interfaz_medica_visita ADD COLUMN IF NOT EXISTS estado_medicacion_concomitante TEXT")
        c.execute("ALTER TABLE interfaz_medica_visita ADD COLUMN IF NOT EXISTS estado_aes TEXT")
        c.execute("ALTER TABLE interfaz_medica_visita ADD COLUMN IF NOT EXISTS estado_decision TEXT")
        c.execute("ALTER TABLE interfaz_medica_visita ADD COLUMN IF NOT EXISTS nota_clinica TEXT")
        c.execute("ALTER TABLE interfaz_medica_visita ADD COLUMN IF NOT EXISTS ultima_actualizacion TEXT")
    else:
        for col_sql in (
            "ALTER TABLE revision_ocular ADD COLUMN sede TEXT",
            "ALTER TABLE revision_ocular ADD COLUMN medico TEXT",
            "ALTER TABLE revision_ocular ADD COLUMN agenda_hospitalaria TEXT",
            "ALTER TABLE revision_ocular ADD COLUMN fecha_evaluacion TEXT",
            "ALTER TABLE revision_ocular ADD COLUMN fechas_previas TEXT",
            "ALTER TABLE revision_ocular ADD COLUMN resultado TEXT",
        ):
            try:
                c.execute(col_sql)
            except Exception:
                pass

    # Persistimos el esquema antes del mantenimiento: si luego hay rollback por deadlock,
    # no se pierden tablas nuevas en despliegues concurrentes.
    conn.commit()

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

@st.cache_data(show_spinner=False, ttl=3)
def get_visitas():
    conn = connect_db()
    try:
        df = pd.read_sql("SELECT * FROM visitas", conn)
    except:
        df = pd.DataFrame()
    conn.close()
    if not df.empty and "ensayo" in df.columns:
        df["ensayo"] = df["ensayo"].fillna("").astype(str).apply(normalizar_ensayo)
        df = filtrar_visitas_importadas_dreamm10(df)
    return df

@st.cache_data(show_spinner=False, ttl=3)
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


@st.cache_data(show_spinner=False, ttl=3)
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
    try:
        c.execute("DELETE FROM interfaz_medica_visita WHERE visita_id=?", (id_visita,))
    except Exception:
        pass
    c.execute("DELETE FROM visitas WHERE id=?", (id_visita,))
    sincronizar_pacientes_desde_visitas(c)
    eliminar_ensayos_sin_pacientes(c)
    conn.commit()
    conn.close()
    invalidar_cache_lecturas()
    snapshot_db("pacientes")


def borrar_paciente_citas_ojos(codigo, nombre):
    codigo_norm_ref = normalizar_clave_paciente(codigo)
    nombre_norm_ref = normalizar_clave_paciente(nombre)
    if not codigo_norm_ref and not nombre_norm_ref:
        return 0

    conn = connect_db()
    c = conn.cursor()
    filas = c.execute("SELECT id, codigo, nombre, ensayo FROM visitas").fetchall()

    ids_borrar = []
    for fila_id, codigo_db, nombre_db, ensayo_db in filas:
        ensayo_norm = _normalizar_ensayo_ojos(ensayo_db)
        if ensayo_norm not in ENSAYOS_OJOS_PERMITIDOS:
            continue

        codigo_norm = normalizar_clave_paciente(codigo_db)
        nombre_norm = normalizar_clave_paciente(nombre_db)

        coincide = False
        if codigo_norm_ref:
            coincide = codigo_norm == codigo_norm_ref
        elif nombre_norm_ref:
            coincide = nombre_norm == nombre_norm_ref

        if coincide:
            ids_borrar.append(int(fila_id))

    if not ids_borrar:
        conn.close()
        return 0

    placeholders = ",".join(["?"] * len(ids_borrar))
    try:
        c.execute(f"DELETE FROM interfaz_medica_visita WHERE visita_id IN ({placeholders})", tuple(ids_borrar))
    except Exception:
        pass
    c.execute(f"DELETE FROM revision_ocular WHERE visita_id IN ({placeholders})", tuple(ids_borrar))
    c.execute(f"DELETE FROM visitas WHERE id IN ({placeholders})", tuple(ids_borrar))

    sincronizar_pacientes_desde_visitas(c)
    eliminar_ensayos_sin_pacientes(c)
    conn.commit()
    conn.close()

    invalidar_cache_lecturas()
    snapshot_db("pacientes")
    return len(ids_borrar)


def borrar_visitas_sin_paciente_citas_ojos():
    conn = connect_db()
    c = conn.cursor()
    filas = c.execute("SELECT id, codigo, nombre, ensayo FROM visitas").fetchall()

    ids_borrar = []
    for fila_id, codigo_db, nombre_db, ensayo_db in filas:
        ensayo_norm = _normalizar_ensayo_ojos(ensayo_db)
        if ensayo_norm not in ENSAYOS_OJOS_PERMITIDOS:
            continue

        codigo_norm = normalizar_clave_paciente(codigo_db)
        nombre_norm = normalizar_clave_paciente(nombre_db)
        if not codigo_norm and not nombre_norm:
            ids_borrar.append(int(fila_id))

    if not ids_borrar:
        conn.close()
        return 0

    placeholders = ",".join(["?"] * len(ids_borrar))
    try:
        c.execute(f"DELETE FROM interfaz_medica_visita WHERE visita_id IN ({placeholders})", tuple(ids_borrar))
    except Exception:
        pass
    c.execute(f"DELETE FROM revision_ocular WHERE visita_id IN ({placeholders})", tuple(ids_borrar))
    c.execute(f"DELETE FROM visitas WHERE id IN ({placeholders})", tuple(ids_borrar))

    sincronizar_pacientes_desde_visitas(c)
    eliminar_ensayos_sin_pacientes(c)
    conn.commit()
    conn.close()

    invalidar_cache_lecturas()
    snapshot_db("pacientes")
    return len(ids_borrar)


def _json_a_dict_seguro(raw_valor):
    if not raw_valor:
        return {}
    try:
        valor = json.loads(raw_valor)
        return valor if isinstance(valor, dict) else {}
    except Exception:
        return {}


def _normalizar_lista_texto(raw_valor):
    texto = str(raw_valor or "")
    partes = re.split(r"[\n,;|]+", texto)
    return [p.strip() for p in partes if p and p.strip()]


def _estado_base_interfaz_medica(visita_row):
    otras = _normalizar_lista_texto(visita_row.get("otras_pruebas", ""))
    if bool(visita_row.get("medula")):
        otras = ["Aspirado de medula"] + otras

    return {
        "estado_constantes": {
            "tension_arterial": "",
            "fc": "",
            "fr": "",
            "temperatura": "",
            "sat_o2": "",
            "peso": "",
            "talla": "",
            "imc": "",
            "superficie_corporal": "",
        },
        "estado_comentarios": {
            "sintomas": [],
            "comentario_libre": str(visita_row.get("comentarios", "") or ""),
            "estado_general": "",
        },
        "estado_pruebas": {
            "pruebas": otras,
            "realizadas": [],
        },
        "estado_farmacos_estudio": {
            "farmacos": [],
        },
        "estado_medicacion_concomitante": {
            "medicaciones": [],
        },
        "estado_aes": {
            "eventos": [],
        },
        "estado_decision": {
            "decision": "Pendiente",
            "accion": "",
            "motivo": "",
        },
        "nota_clinica": "",
    }


def _es_error_tabla_interfaz_no_existe(exc):
    txt = str(exc or "").lower()
    return (
        "interfaz_medica_visita" in txt
        and (
            "does not exist" in txt
            or "undefinedtable" in txt
            or "no such table" in txt
        )
    )


def _crear_tabla_interfaz_medica_si_falta(cursor):
    if DB_BACKEND == "postgres":
        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS interfaz_medica_visita (
                id BIGSERIAL PRIMARY KEY,
                visita_id BIGINT UNIQUE,
                estado_constantes TEXT,
                estado_comentarios TEXT,
                estado_pruebas TEXT,
                estado_farmacos_estudio TEXT,
                estado_medicacion_concomitante TEXT,
                estado_aes TEXT,
                estado_decision TEXT,
                nota_clinica TEXT,
                ultima_actualizacion TEXT
            )
            '''
        )
    else:
        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS interfaz_medica_visita (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                visita_id INTEGER UNIQUE,
                estado_constantes TEXT,
                estado_comentarios TEXT,
                estado_pruebas TEXT,
                estado_farmacos_estudio TEXT,
                estado_medicacion_concomitante TEXT,
                estado_aes TEXT,
                estado_decision TEXT,
                nota_clinica TEXT,
                ultima_actualizacion TEXT,
                FOREIGN KEY(visita_id) REFERENCES visitas(id)
            )
            '''
        )


def get_estado_interfaz_medica(visita_row):
    visita_id = int(visita_row.get("id"))
    estado = _estado_base_interfaz_medica(visita_row)
    conn = connect_db()
    c = conn.cursor()
    try:
        fila = c.execute(
            '''
            SELECT estado_constantes, estado_comentarios, estado_pruebas,
                   estado_farmacos_estudio, estado_medicacion_concomitante,
                   estado_aes, estado_decision, nota_clinica
            FROM interfaz_medica_visita
            WHERE visita_id = ?
            ''',
            (visita_id,)
        ).fetchone()
    except Exception as exc:
        if _es_error_tabla_interfaz_no_existe(exc):
            try:
                _crear_tabla_interfaz_medica_si_falta(c)
                conn.commit()
                fila = None
            except Exception:
                fila = None
        else:
            fila = None
    conn.close()

    if not fila:
        return estado

    columnas = [
        "estado_constantes",
        "estado_comentarios",
        "estado_pruebas",
        "estado_farmacos_estudio",
        "estado_medicacion_concomitante",
        "estado_aes",
        "estado_decision",
    ]
    for idx, col in enumerate(columnas):
        base_dict = estado.get(col, {})
        guardado = _json_a_dict_seguro(fila[idx])
        if isinstance(base_dict, dict):
            base_dict.update(guardado)
            estado[col] = base_dict
        else:
            estado[col] = guardado

    estado["nota_clinica"] = str(fila[7] or "")
    return estado


def guardar_estado_interfaz_medica(visita_id, estado):
    visita_id = int(visita_id)
    conn = connect_db()
    c = conn.cursor()
    try:
        existe = c.execute(
            "SELECT id FROM interfaz_medica_visita WHERE visita_id = ?",
            (visita_id,),
        ).fetchone()
    except Exception as exc:
        if _es_error_tabla_interfaz_no_existe(exc):
            try:
                _crear_tabla_interfaz_medica_si_falta(c)
                conn.commit()
                existe = c.execute(
                    "SELECT id FROM interfaz_medica_visita WHERE visita_id = ?",
                    (visita_id,),
                ).fetchone()
            except Exception:
                conn.rollback()
                conn.close()
                return
        else:
            conn.rollback()
            conn.close()
            return

    payload = {
        "estado_constantes": json.dumps(estado.get("estado_constantes", {}), ensure_ascii=False),
        "estado_comentarios": json.dumps(estado.get("estado_comentarios", {}), ensure_ascii=False),
        "estado_pruebas": json.dumps(estado.get("estado_pruebas", {}), ensure_ascii=False),
        "estado_farmacos_estudio": json.dumps(estado.get("estado_farmacos_estudio", {}), ensure_ascii=False),
        "estado_medicacion_concomitante": json.dumps(estado.get("estado_medicacion_concomitante", {}), ensure_ascii=False),
        "estado_aes": json.dumps(estado.get("estado_aes", {}), ensure_ascii=False),
        "estado_decision": json.dumps(estado.get("estado_decision", {}), ensure_ascii=False),
        "nota_clinica": str(estado.get("nota_clinica", "") or ""),
        "ultima_actualizacion": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    try:
        if existe:
            c.execute(
                '''
                UPDATE interfaz_medica_visita
                SET estado_constantes = ?, estado_comentarios = ?, estado_pruebas = ?,
                    estado_farmacos_estudio = ?, estado_medicacion_concomitante = ?,
                    estado_aes = ?, estado_decision = ?, nota_clinica = ?,
                    ultima_actualizacion = ?
                WHERE visita_id = ?
                ''',
                (
                    payload["estado_constantes"],
                    payload["estado_comentarios"],
                    payload["estado_pruebas"],
                    payload["estado_farmacos_estudio"],
                    payload["estado_medicacion_concomitante"],
                    payload["estado_aes"],
                    payload["estado_decision"],
                    payload["nota_clinica"],
                    payload["ultima_actualizacion"],
                    visita_id,
                ),
            )
        else:
            c.execute(
                '''
                INSERT INTO interfaz_medica_visita (
                    visita_id, estado_constantes, estado_comentarios, estado_pruebas,
                    estado_farmacos_estudio, estado_medicacion_concomitante, estado_aes,
                    estado_decision, nota_clinica, ultima_actualizacion
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    visita_id,
                    payload["estado_constantes"],
                    payload["estado_comentarios"],
                    payload["estado_pruebas"],
                    payload["estado_farmacos_estudio"],
                    payload["estado_medicacion_concomitante"],
                    payload["estado_aes"],
                    payload["estado_decision"],
                    payload["nota_clinica"],
                    payload["ultima_actualizacion"],
                ),
            )
        conn.commit()
    except Exception:
        conn.rollback()
    conn.close()


def _listar_bases_backup_locales():
    candidatos = []

    if os.path.isfile(os.path.join(SCRIPT_DIR, "agenda_ensayos_backup_2026-03-06_124925.db")):
        candidatos.append(os.path.join(SCRIPT_DIR, "agenda_ensayos_backup_2026-03-06_124925.db"))

    candidatos.extend(sorted(glob.glob(os.path.join(DB_BACKUP_DIR, "*.db"))))
    candidatos.extend(sorted(glob.glob(os.path.join(SCRIPT_DIR, "agenda_ensayos_backup_*.db"))))

    vistos = set()
    ordenados = []
    for ruta in candidatos:
        ruta_abs = os.path.abspath(ruta)
        if not os.path.isfile(ruta_abs):
            continue
        if ruta_abs == os.path.abspath(DB_PATH):
            continue
        if ruta_abs in vistos:
            continue
        vistos.add(ruta_abs)
        ordenados.append(ruta_abs)

    ordenados.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return ordenados


def restaurar_paciente_desde_backups_locales(codigo):
    codigo = normalizar_texto_campo(codigo)
    if not codigo:
        return {
            "ok": False,
            "mensaje": "Introduce un código de paciente.",
            "backups": 0,
            "visitas_insertadas": 0,
            "visitas_totales": 0,
        }

    backups = _listar_bases_backup_locales()
    if not backups:
        return {
            "ok": False,
            "mensaje": "No se encontraron backups locales en la carpeta de la app.",
            "backups": 0,
            "visitas_insertadas": 0,
            "visitas_totales": 0,
        }

    conn = connect_db()
    c = conn.cursor()
    visitas_insertadas = 0
    paciente_encontrado = False
    visitas_backup = 0

    for ruta_backup in backups:
        try:
            src = sqlite3.connect(ruta_backup)
        except Exception:
            continue

        try:
            s = src.cursor()
            p_row = s.execute(
                "SELECT codigo, nombre, ensayo FROM pacientes WHERE codigo = ? ORDER BY id DESC LIMIT 1",
                (codigo,),
            ).fetchone()
            v_rows = s.execute(
                """
                SELECT fecha, nombre, codigo, ensayo, ciclo, kits, tablet, medula, otras_pruebas, comentarios
                FROM visitas
                WHERE codigo = ?
                ORDER BY id ASC
                """,
                (codigo,),
            ).fetchall()
        except Exception:
            src.close()
            continue

        if not p_row and not v_rows:
            src.close()
            continue

        paciente_encontrado = True
        visitas_backup += len(v_rows)

        if p_row:
            codigo_p = normalizar_texto_campo(p_row[0])
            nombre_p = nombre_a_iniciales(p_row[1])
            ensayo_p = normalizar_ensayo(p_row[2])
            existe_p = c.execute("SELECT id FROM pacientes WHERE codigo = ?", (codigo_p,)).fetchone()
            if existe_p:
                c.execute(
                    "UPDATE pacientes SET nombre = ?, ensayo = ? WHERE codigo = ?",
                    (nombre_p, ensayo_p, codigo_p),
                )
            else:
                c.execute(
                    "INSERT OR IGNORE INTO pacientes (codigo, nombre, ensayo) VALUES (?, ?, ?)",
                    (codigo_p, nombre_p, ensayo_p),
                )

        for fila in v_rows:
            fecha, nombre, codigo_v, ensayo, ciclo, kits, tablet, medula, otras_pruebas, comentarios = fila
            codigo_v = normalizar_texto_campo(codigo_v) or codigo
            nombre_v = nombre_a_iniciales(nombre)
            ensayo_v = normalizar_ensayo(ensayo)

            existe_v = c.execute(
                """
                SELECT 1
                FROM visitas
                WHERE codigo = ?
                  AND fecha = ?
                  AND COALESCE(ciclo, '') = COALESCE(?, '')
                  AND COALESCE(comentarios, '') = COALESCE(?, '')
                LIMIT 1
                """,
                (codigo_v, fecha, ciclo, comentarios),
            ).fetchone()
            if existe_v:
                continue

            c.execute(
                """
                INSERT INTO visitas (fecha, nombre, codigo, ensayo, ciclo, kits, tablet, medula, otras_pruebas, comentarios)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fecha,
                    nombre_v,
                    codigo_v,
                    ensayo_v,
                    ciclo,
                    kits,
                    tablet,
                    medula,
                    otras_pruebas,
                    comentarios,
                ),
            )
            visitas_insertadas += 1

        src.close()

    if not paciente_encontrado:
        conn.close()
        return {
            "ok": False,
            "mensaje": f"No se encontró el código {codigo} en los backups locales.",
            "backups": len(backups),
            "visitas_insertadas": 0,
            "visitas_totales": 0,
        }

    sincronizar_pacientes_desde_visitas(c)
    unificar_pacientes_duplicados(c)
    eliminar_ensayos_sin_pacientes(c)
    conn.commit()

    visitas_totales = c.execute("SELECT COUNT(*) FROM visitas WHERE codigo = ?", (codigo,)).fetchone()[0]
    conn.close()

    invalidar_cache_lecturas()
    snapshot_db("pacientes")

    return {
        "ok": True,
        "mensaje": f"Paciente {codigo} recuperado desde backups locales.",
        "backups": len(backups),
        "visitas_insertadas": int(visitas_insertadas),
        "visitas_totales": int(visitas_totales),
        "visitas_backup": int(visitas_backup),
    }

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
        "INSERT INTO checklist_items (ensayo, item, done) VALUES (?, ?, ?)",
        (ensayo, item, False)
    )
    conn.commit()
    conn.close()
    invalidar_cache_lecturas()

def add_checklist_items_bulk(ensayo, items):
    ensayo = normalizar_ensayo(ensayo)
    if not items:
        return 0
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
        nuevos = [(ensayo, item, False) for ensayo, item in nuevos]
        c.executemany(
            "INSERT INTO checklist_items (ensayo, item, done) VALUES (?, ?, ?)",
            nuevos
        )
    conn.commit()
    conn.close()
    invalidar_cache_lecturas()
    return len(nuevos)

def set_checklist_done(item_id, done):
    conn = connect_db()
    c = conn.cursor()
    c.execute("UPDATE checklist_items SET done = ? WHERE id = ?", (bool(done), item_id))
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


def add_nota_coordinacion(fecha_nota, texto, urgencia):
    conn = connect_db()
    c = conn.cursor()
    creado_en = ahora_local().isoformat(timespec="seconds")
    c.execute(
        """
        INSERT INTO notas_coordinacion (fecha_nota, texto, urgencia, creado_en)
        VALUES (?, ?, ?, ?)
        """,
        (fecha_nota, texto, urgencia, creado_en)
    )
    conn.commit()
    conn.close()
    invalidar_cache_lecturas()


@st.cache_data(show_spinner=False)
def get_notas_coordinacion():
    conn = connect_db()
    try:
        df = pd.read_sql(
            """
            SELECT id, fecha_nota, texto, urgencia, creado_en
            FROM notas_coordinacion
            ORDER BY creado_en ASC, id ASC
            """,
            conn
        )
    except Exception:
        df = pd.DataFrame(columns=["id", "fecha_nota", "texto", "urgencia", "creado_en"])
    conn.close()
    return df


def delete_nota_coordinacion(nota_id):
    conn = connect_db()
    c = conn.cursor()
    c.execute("DELETE FROM notas_coordinacion WHERE id = ?", (nota_id,))
    conn.commit()
    conn.close()
    invalidar_cache_lecturas()


def guardar_adenda_ensayo(ensayo, texto):
    ensayo = normalizar_ensayo(ensayo)
    if not ensayo:
        return
    conn = connect_db()
    c = conn.cursor()
    fecha_mod = ahora_local().isoformat(timespec="seconds")
    c.execute(
        """
        UPDATE adendas_ensayo
        SET texto = ?, fecha_modificacion = ?
        WHERE ensayo = ?
        """,
        (texto, fecha_mod, ensayo)
    )
    if c.rowcount == 0:
        c.execute(
            """
            INSERT INTO adendas_ensayo (ensayo, texto, fecha_modificacion)
            VALUES (?, ?, ?)
            """,
            (ensayo, texto, fecha_mod)
        )
    conn.commit()
    conn.close()
    invalidar_cache_lecturas()


def guardar_adenda_paciente(codigo, nombre, ensayo, texto):
    codigo = normalizar_texto_campo(codigo)
    nombre = nombre_a_iniciales(nombre)
    ensayo = normalizar_ensayo(ensayo)
    clave = clave_paciente_unificada(codigo, nombre, ensayo)
    if not clave:
        return

    conn = connect_db()
    c = conn.cursor()
    fecha_mod = ahora_local().isoformat(timespec="seconds")
    c.execute(
        """
        UPDATE adendas_paciente
        SET codigo = ?, nombre = ?, ensayo = ?, texto = ?, fecha_modificacion = ?
        WHERE clave_paciente = ?
        """,
        (codigo, nombre, ensayo, texto, fecha_mod, clave)
    )
    if c.rowcount == 0:
        c.execute(
            """
            INSERT INTO adendas_paciente (
                clave_paciente, codigo, nombre, ensayo, texto, fecha_modificacion
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (clave, codigo, nombre, ensayo, texto, fecha_mod)
        )
    conn.commit()
    conn.close()
    invalidar_cache_lecturas()


@st.cache_data(show_spinner=False)
def get_adenda_paciente(codigo, nombre, ensayo):
    codigo = normalizar_texto_campo(codigo)
    nombre = nombre_a_iniciales(nombre)
    ensayo = normalizar_ensayo(ensayo)
    clave = clave_paciente_unificada(codigo, nombre, ensayo)
    if not clave:
        return {"texto": "", "fecha_modificacion": ""}

    conn = connect_db()
    try:
        c = conn.cursor()
        c.execute(
            """
            SELECT texto, fecha_modificacion
            FROM adendas_paciente
            WHERE clave_paciente = ?
            """,
            (clave,)
        )
        row = c.fetchone()
    except Exception:
        row = None
    conn.close()

    if not row:
        return {"texto": "", "fecha_modificacion": ""}
    return {
        "texto": "" if row[0] is None else str(row[0]),
        "fecha_modificacion": "" if row[1] is None else str(row[1])
    }


@st.cache_data(show_spinner=False)
def get_pacientes_con_adenda(ensayo):
    ensayo = normalizar_ensayo(ensayo)
    conn = connect_db()
    try:
        df = pd.read_sql(
            """
            SELECT codigo, nombre, texto, fecha_modificacion
            FROM adendas_paciente
            WHERE ensayo = ?
            ORDER BY codigo ASC, nombre ASC
            """,
            conn,
            params=(ensayo,)
        )
    except Exception:
        df = pd.DataFrame(columns=["codigo", "nombre", "texto", "fecha_modificacion"])
    conn.close()

    if df.empty:
        return df

    if "texto" in df.columns:
        texto_limpio = (
            df["texto"]
            .fillna("")
            .astype(str)
            .str.replace(r"[\s\u200b\u200c\u200d\ufeff]+", "", regex=True)
        )
        df = df[texto_limpio != ""].copy()
        df = df[["codigo", "nombre", "fecha_modificacion"]]

    return df


@st.cache_data(show_spinner=False)
def get_adendas_ensayo():
    conn = connect_db()
    try:
        df = pd.read_sql(
            """
            SELECT id, ensayo, texto, fecha_modificacion
            FROM adendas_ensayo
            ORDER BY ensayo ASC
            """,
            conn
        )
    except Exception:
        df = pd.DataFrame(columns=["id", "ensayo", "texto", "fecha_modificacion"])
    conn.close()
    return df


@st.cache_data(show_spinner=False)
def get_ensayos_con_adendas_pendientes():
    conn = connect_db()

    def _filtrar_texto_no_vacio(df_in):
        if df_in is None or df_in.empty or "texto" not in df_in.columns:
            return pd.DataFrame(columns=["ensayo", "codigo", "nombre", "texto"])
        df_local = df_in.copy()
        texto_limpio = (
            df_local["texto"]
            .fillna("")
            .astype(str)
            .str.replace(r"[\s\u200b\u200c\u200d\ufeff]+", "", regex=True)
        )
        df_local = df_local[texto_limpio != ""].copy()
        for col in ["ensayo", "codigo", "nombre"]:
            if col not in df_local.columns:
                df_local[col] = ""
        return df_local[["ensayo", "codigo", "nombre", "texto"]]

    try:
        df_paciente = pd.read_sql(
            """
            SELECT ensayo, codigo, nombre, texto
            FROM adendas_paciente
            ORDER BY ensayo ASC, codigo ASC, nombre ASC
            """,
            conn
        )
    except Exception:
        df_paciente = pd.DataFrame(columns=["ensayo", "codigo", "nombre", "texto"])

    conn.close()

    df_paciente = _filtrar_texto_no_vacio(df_paciente)
    if df_paciente.empty:
        return []

    df = df_paciente.copy()
    if df.empty or "ensayo" not in df.columns:
        return []

    vistos = set()

    pendientes = []
    for _, row in df.iterrows():
        ensayo = "" if pd.isna(row.get("ensayo")) else str(row.get("ensayo")).strip()
        codigo = "" if pd.isna(row.get("codigo")) else str(row.get("codigo")).strip()
        nombre = "" if pd.isna(row.get("nombre")) else str(row.get("nombre")).strip()
        if not ensayo:
            continue
        paciente = f"{codigo} | {nombre}".strip(" |")
        etiqueta = f"{ensayo} • {paciente}" if paciente else ensayo
        clave = (ensayo.lower(), paciente.lower())
        if clave in vistos:
            continue
        vistos.add(clave)
        pendientes.append({
            "ensayo": ensayo,
            "paciente": paciente,
            "etiqueta": etiqueta,
        })
    return pendientes


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


def guardar_revision_ocular(visita_id, sede, medico, agenda_hospitalaria, fecha_evaluacion, resultado):
    sede = str(sede or "").strip().lower()
    medico = str(medico or "").strip().upper()
    if medico and medico not in MEDICOS_OJOS_PERMITIDOS:
        medico = "OTRO"
    agenda_hospitalaria = str(agenda_hospitalaria or "").strip()
    fecha_evaluacion = str(fecha_evaluacion or "").strip()
    resultado = str(resultado or "").strip()

    kva = None
    m = re.search(r"\bKVA\s*([0-4])\b", resultado.upper())
    if m:
        try:
            kva = int(m.group(1))
        except Exception:
            kva = None

    conn = connect_db()
    c = conn.cursor()

    # Sincronizamos la revision ocular entre todas las visitas del mismo paciente.
    filas_visitas = c.execute(
        "SELECT id, codigo, nombre, ensayo FROM visitas ORDER BY id DESC"
    ).fetchall()

    clave_ref = ""
    for fila_id, codigo_ref, nombre_ref, ensayo_ref in filas_visitas:
        if int(fila_id) == int(visita_id):
            clave_ref = clave_paciente_unificada(codigo_ref, nombre_ref, ensayo_ref)
            break

    if clave_ref:
        visita_ids_objetivo = [
            int(fila_id)
            for fila_id, codigo_ref, nombre_ref, ensayo_ref in filas_visitas
            if clave_paciente_unificada(codigo_ref, nombre_ref, ensayo_ref) == clave_ref
        ]
    else:
        visita_ids_objetivo = [int(visita_id)]

    for visita_id_destino in visita_ids_objetivo:
        c.execute(
            """
            SELECT fecha_evaluacion, fecha_cita, fechas_previas
            FROM revision_ocular
            WHERE visita_id = ?
            """,
            (visita_id_destino,)
        )
        previa = c.fetchone()

        historial_fechas = []
        if previa:
            fechas_previas_raw = "" if previa[2] is None else str(previa[2]).strip()
            if fechas_previas_raw:
                historial_fechas = [f.strip() for f in fechas_previas_raw.split(" | ") if f.strip()]

            fecha_actual = ""
            if previa[0] is not None and str(previa[0]).strip():
                fecha_actual = str(previa[0]).strip()
            elif previa[1] is not None and str(previa[1]).strip():
                fecha_actual = str(previa[1]).strip()

            if fecha_actual and fecha_actual != fecha_evaluacion and fecha_actual not in historial_fechas:
                historial_fechas.append(fecha_actual)

        fechas_previas_txt = " | ".join(historial_fechas)

        c.execute(
            """
            UPDATE revision_ocular
            SET sede = ?, medico = ?, agenda_hospitalaria = ?, fecha_evaluacion = ?, fechas_previas = ?, resultado = ?,
                fecha_cita = ?, kva = ?
            WHERE visita_id = ?
            """,
            (sede, medico, agenda_hospitalaria, fecha_evaluacion, fechas_previas_txt, resultado, fecha_evaluacion, kva, visita_id_destino)
        )
        if c.rowcount == 0:
            c.execute(
                """
                INSERT INTO revision_ocular (
                    visita_id, sede, medico, agenda_hospitalaria, fecha_evaluacion, fechas_previas, resultado, fecha_cita, kva
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (visita_id_destino, sede, medico, agenda_hospitalaria, fecha_evaluacion, "", resultado, fecha_evaluacion, kva)
            )
    conn.commit()
    conn.close()
    invalidar_cache_lecturas()

@st.cache_data(show_spinner=False)
def get_revision_ocular(visita_id):
    conn = connect_db()
    c = conn.cursor()
    c.execute(
        """
        SELECT sede, medico, agenda_hospitalaria, fecha_evaluacion, fechas_previas, resultado, fecha_cita, kva
        FROM revision_ocular
        WHERE visita_id=?
        """,
        (visita_id,)
    )
    row = c.fetchone()
    conn.close()
    if not row:
        return {
            "sede": "",
            "medico": "",
            "agenda_hospitalaria": "",
            "fecha_evaluacion": "",
            "resultado": "",
        }

    sede, medico, agenda_hospitalaria, fecha_evaluacion, fechas_previas, resultado, fecha_cita, kva = row
    fecha_eval_final = fecha_evaluacion if fecha_evaluacion else (fecha_cita or "")
    if resultado:
        resultado_final = str(resultado)
    elif kva is not None:
        resultado_final = f"KVA {int(kva)}"
    else:
        resultado_final = ""

    return {
        "sede": "" if sede is None else str(sede),
        "medico": "" if medico is None else str(medico),
        "agenda_hospitalaria": "" if agenda_hospitalaria is None else str(agenda_hospitalaria),
        "fecha_evaluacion": "" if fecha_eval_final is None else str(fecha_eval_final),
        "fechas_previas": "" if fechas_previas is None else str(fechas_previas),
        "resultado": resultado_final,
    }


@st.cache_data(show_spinner=False)
def get_revisiones_oculares_df():
    conn = connect_db()
    try:
        df = pd.read_sql(
            """
            SELECT visita_id, sede, medico, agenda_hospitalaria, fecha_evaluacion, fechas_previas, resultado, fecha_cita, kva
            FROM revision_ocular
            """,
            conn
        )
    except Exception:
        df = pd.DataFrame(
            columns=[
                "visita_id",
                "sede",
                "medico",
                "agenda_hospitalaria",
                "fecha_evaluacion",
                "fechas_previas",
                "resultado",
                "fecha_cita",
                "kva",
            ]
        )
    conn.close()

    if "fecha_evaluacion" not in df.columns:
        df["fecha_evaluacion"] = None
    if "fecha_cita" not in df.columns:
        df["fecha_cita"] = None
    if "resultado" not in df.columns:
        df["resultado"] = None
    if "kva" not in df.columns:
        df["kva"] = None
    if "sede" not in df.columns:
        df["sede"] = None
    if "agenda_hospitalaria" not in df.columns:
        df["agenda_hospitalaria"] = None
    if "fechas_previas" not in df.columns:
        df["fechas_previas"] = None

    df["fecha_evaluacion"] = df["fecha_evaluacion"].fillna(df["fecha_cita"])
    df["resultado"] = df.apply(
        lambda r: (
            str(r["resultado"])
            if pd.notna(r["resultado"]) and str(r["resultado"]).strip()
            else (f"KVA {int(r['kva'])}" if pd.notna(r["kva"]) else "")
        ),
        axis=1,
    )
    return df


def invalidar_cache_lecturas():
    get_visitas.clear()
    get_pacientes_unicos.clear()
    get_ensayos_existentes.clear()
    get_checklist_items.clear()
    get_notas_enfermeria.clear()
    get_notas_coordinacion.clear()
    get_adendas_ensayo.clear()
    get_adenda_paciente.clear()
    get_pacientes_con_adenda.clear()
    get_ensayos_con_adendas_pendientes.clear()
    get_revision_ocular.clear()
    get_revisiones_oculares_df.clear()


ENSAYOS_OJOS_PERMITIDOS = ["DREAMM 10", "DREAMM-8", "Fuera de Ensayo"]
MEDICOS_OJOS_PERMITIDOS = ["ISABEL", "ANTONIO", "ROCIO", "OTRO"]


def _normalizar_ensayo_ojos(valor):
    txt = normalizar_ensayo(valor)
    base = re.sub(r"[^A-Z0-9]", "", str(txt or "").upper())
    if base == "DREAMM10":
        return "DREAMM 10"
    if base == "DREAMM8":
        return "DREAMM-8"
    if base == "FUERADEENSAYO":
        return "Fuera de Ensayo"
    return txt


def actualizar_ensayo_visita(id_visita, nuevo_ensayo):
    nuevo_ensayo = _normalizar_ensayo_ojos(nuevo_ensayo)
    conn = connect_db()
    c = conn.cursor()
    c.execute("UPDATE visitas SET ensayo = ? WHERE id = ?", (nuevo_ensayo, id_visita))
    sincronizar_pacientes_desde_visitas(c)
    unificar_pacientes_duplicados(c)
    eliminar_ensayos_sin_pacientes(c)
    conn.commit()
    conn.close()
    invalidar_cache_lecturas()

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

_NOMBRES_FEMENINOS = {
    "maria","ana","laura","carmen","rosa","elena","lucia","marta","paula","sara",
    "isabel","patricia","cristina","andrea","raquel","silvia","monica","natalia",
    "beatriz","pilar","teresa","concepcion","dolores","josefa","manuela","francisca",
    "mercedes","antonia","fatima","amparo","gloria","encarnacion","trinidad","yolanda",
    "sonia","diana","irene","eva","alba","nuria","alicia","claudia","sofia","julia",
    "leticia","lorena","miriam","esther","rocio","inmaculada","angela",
}
_NOMBRES_MASCULINOS = {
    "jose","antonio","manuel","francisco","juan","david","carlos","jesus","miguel",
    "angel","pedro","pablo","rafael","alejandro","javier","alberto","sergio","jorge",
    "roberto","fernando","daniel","luis","mario","jorge","ricardo","ivan","gonzalo",
    "alvaro","marcos","diego","julian","emilio","jaime","hugo","victor","hector",
    "cesar","ignacio","felix","tomas","ramon","andres","enrique","nicolas","eduardo",
}

def _inferir_sexo(nombre):
    """Heurística por primer nombre; devuelve 'F' o 'M'."""
    if not nombre:
        return "M"
    primer = nombre.strip().split()[0].lower().rstrip(".")
    if primer in _NOMBRES_FEMENINOS:
        return "F"
    if primer in _NOMBRES_MASCULINOS:
        return "M"
    # Fallback: nombres terminados en 'a' → F, resto → M
    return "F" if primer.endswith("a") else "M"


_SVG_SILUETA_M = (
    '<svg viewBox="0 0 40 72" xmlns="http://www.w3.org/2000/svg" fill="currentColor">'
    '<circle cx="20" cy="11" r="9"/>'
    '<rect x="11" y="22" width="18" height="22" rx="4"/>'
    '<rect x="11" y="43" width="7" height="20" rx="3.5"/>'
    '<rect x="22" y="43" width="7" height="20" rx="3.5"/>'
    '<rect x="2" y="22" width="8" height="18" rx="4"/>'
    '<rect x="30" y="22" width="8" height="18" rx="4"/>'
    '</svg>'
)
_SVG_SILUETA_F = (
    '<svg viewBox="0 0 40 72" xmlns="http://www.w3.org/2000/svg" fill="currentColor">'
    '<circle cx="20" cy="11" r="9"/>'
    '<path d="M10 22 L5 55 L16 55 L20 38 L24 55 L35 55 L30 22 Z"/>'
    '<rect x="2" y="22" width="7" height="16" rx="3.5"/>'
    '<rect x="31" y="22" width="7" height="16" rx="3.5"/>'
    '</svg>'
)


def _get_estado_visita_anterior(df_visitas_all, visita_row):
    """Devuelve el estado guardado en interfaz_medica_visita de la visita previa del mismo paciente."""
    cod = str(visita_row.get("codigo", "") or "").strip()
    ens = str(visita_row.get("ensayo", "") or "").strip()
    nom = str(visita_row.get("nombre", "") or "").strip()
    fecha_actual = pd.to_datetime(str(visita_row.get("fecha", "") or ""), errors="coerce")

    mask = (
        df_visitas_all["ensayo"].str.strip().str.casefold() == ens.casefold()
    )
    if cod:
        mask = mask & (df_visitas_all["codigo"].str.strip().str.casefold() == cod.casefold())
    else:
        mask = mask & (df_visitas_all["nombre"].str.strip().str.casefold() == nom.casefold())

    anteriores = df_visitas_all[mask].copy()
    anteriores["_fdt"] = pd.to_datetime(anteriores["fecha"], errors="coerce")
    if pd.notna(fecha_actual):
        anteriores = anteriores[anteriores["_fdt"] < fecha_actual]
    anteriores = anteriores.sort_values("_fdt", ascending=False)
    if anteriores.empty:
        return None, None

    prev_row = anteriores.iloc[0]
    from_estado = get_estado_interfaz_medica(prev_row)
    return prev_row, from_estado


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

    # Compatibilidad con esquemas heredados (PostgreSQL/SQLite) que pueden
    # no incluir todas las columnas esperadas en calendario.
    df_local = df_visitas.copy()
    defaults = {
        "id": "",
        "nombre": "",
        "codigo": "",
        "ensayo": "",
        "ciclo": "",
        "medula": False,
        "fecha": "",
    }
    for col, default_val in defaults.items():
        if col not in df_local.columns:
            df_local[col] = default_val

    # Normalizamos medula a bool para evitar errores con None/NaN/textos.
    df_local["medula"] = (
        df_local["medula"]
        .fillna(False)
        .apply(lambda v: str(v).strip().lower() in {"1", "true", "t", "si", "sí", "yes", "y"} if isinstance(v, str) else bool(v))
    )

    for _, row in df_local.iterrows():
        titulo_evento = f"🆔 {row.get('codigo', '')} | {row.get('ensayo', '')}"
        if bool(row.get('medula', False)):
            titulo_evento += " 🩸"

        event = {
            "title": titulo_evento,
            "start": row.get('fecha', ''),
            "allDay": True,
            "extendedProps": {
                "id": row.get('id', ''),
                "nombre": row.get('nombre', ''),
                "ciclo": row.get('ciclo', ''),
                "medula": bool(row.get('medula', False)),
                "ensayo": row.get('ensayo', '')
            },
            "backgroundColor": "#ff4b4b" if bool(row.get('medula', False)) else "#3788d8"
        }
        eventos.append(event)

    eventos.extend(generar_visita_teorica_2274(df_local))
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

def listar_excels(directorio):
    if not os.path.isdir(directorio):
        return []
    archivos = [
        f for f in os.listdir(directorio)
        if f.lower().endswith(".xlsx") and os.path.isfile(os.path.join(directorio, f))
    ]
    return sorted(archivos)


def guardar_excel_dreamm10_en_db(nombre_archivo, contenido):
    nombre = os.path.basename(str(nombre_archivo or "")).strip()
    if not nombre or not contenido:
        return False

    marca_tiempo = ahora_local().isoformat(timespec="seconds")
    conn = connect_db()
    c = conn.cursor()
    try:
        c.execute(
            "UPDATE dreamm10_excels SET contenido = ?, actualizado_en = ? WHERE nombre_archivo = ?",
            (contenido, marca_tiempo, nombre),
        )
        if not getattr(c, "rowcount", 0):
            c.execute(
                "INSERT INTO dreamm10_excels (nombre_archivo, contenido, actualizado_en) VALUES (?, ?, ?)",
                (nombre, contenido, marca_tiempo),
            )
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        return False
    finally:
        conn.close()


def obtener_excels_dreamm10_db():
    conn = connect_db()
    c = conn.cursor()
    try:
        filas = c.execute(
            "SELECT nombre_archivo, contenido FROM dreamm10_excels ORDER BY nombre_archivo ASC"
        ).fetchall()
    except Exception:
        conn.close()
        return {}

    resultado = {}
    for nombre, contenido in filas:
        nombre_txt = os.path.basename(str(nombre or "")).strip()
        if not nombre_txt:
            continue
        if contenido is None:
            continue
        if isinstance(contenido, memoryview):
            contenido = contenido.tobytes()
        elif not isinstance(contenido, (bytes, bytearray)):
            try:
                contenido = bytes(contenido)
            except Exception:
                continue
        resultado[nombre_txt] = bytes(contenido)

    conn.close()
    return resultado


@st.cache_data(show_spinner=False)
def cargar_excel_por_hojas(ruta_excel):
    libro = pd.ExcelFile(ruta_excel)
    hojas = {}
    for hoja in libro.sheet_names:
        # Formato actual: variables como encabezados de columna.
        df_hoja = pd.read_excel(libro, sheet_name=hoja, header=0)
        hojas[hoja] = df_hoja
    return hojas


@st.cache_data(show_spinner=False)
def cargar_excel_desde_bytes(bytes_excel):
    buffer = io.BytesIO(bytes_excel)
    libro = pd.ExcelFile(buffer)
    hojas = {}
    for hoja in libro.sheet_names:
        # Formato actual: variables como encabezados de columna.
        df_hoja = pd.read_excel(libro, sheet_name=hoja, header=0)
        hojas[hoja] = df_hoja
    return hojas


@st.cache_data(show_spinner=False)
def leer_archivo_binario(ruta_archivo):
    with open(ruta_archivo, "rb") as f:
        return f.read()


def _normalizar_token_checklist(valor):
    texto = normalizar_texto_campo(valor).upper()
    return re.sub(r"[^A-Z0-9]+", "", texto)


def _extraer_numeros_checklist(valor):
    texto = normalizar_texto_campo(valor)
    return set(re.findall(r"\d{2,}", texto))


def _listar_protocolos_checklist(hojas_excel):
    protocolos = []
    vistos = set()

    for nombre_hoja in ("Visitas_resumen", "Analitos"):
        df = hojas_excel.get(nombre_hoja)
        if df is None or df.empty or "Protocolo" not in df.columns:
            continue

        for protocolo in df["Protocolo"].dropna().astype(str).tolist():
            texto = normalizar_texto_campo(protocolo)
            if not texto:
                continue
            clave = texto.casefold()
            if clave in vistos:
                continue
            vistos.add(clave)
            protocolos.append(texto)

    return protocolos


def _buscar_protocolos_relacionados(ensayo, protocolos):
    ensayo_norm = normalizar_ensayo(ensayo)
    ensayo_txt = normalizar_texto_campo(ensayo_norm)
    ensayo_token = _normalizar_token_checklist(ensayo_txt)
    ensayo_numeros = _extraer_numeros_checklist(ensayo_txt)
    palabras_ensayo = set(re.findall(r"[A-Z0-9]+", ensayo_txt.upper()))

    puntuados = []
    for idx, protocolo in enumerate(protocolos):
        protocolo_txt = normalizar_texto_campo(protocolo)
        protocolo_token = _normalizar_token_checklist(protocolo_txt)
        protocolo_numeros = _extraer_numeros_checklist(protocolo_txt)
        palabras_protocolo = set(re.findall(r"[A-Z0-9]+", protocolo_txt.upper()))

        score = 0
        if ensayo_token and ensayo_token in protocolo_token:
            score += 100
        if ensayo_numeros and ensayo_numeros & protocolo_numeros:
            score += 120
        if ensayo_txt and ensayo_txt.casefold() in protocolo_txt.casefold():
            score += 60

        interseccion_palabras = palabras_ensayo & palabras_protocolo
        if interseccion_palabras:
            score += 10 * len(interseccion_palabras)

        if score > 0:
            puntuados.append((score, idx, protocolo))

    puntuados.sort(key=lambda item: (-item[0], item[1]))
    return [protocolo for _, _, protocolo in puntuados]


def _construir_items_protocolo_desde_excel(hojas_excel, protocolo_sel):
    items = []

    df_visitas = hojas_excel.get("Visitas_resumen")
    if df_visitas is not None and not df_visitas.empty and "Protocolo" in df_visitas.columns:
        df_visitas_filtrado = df_visitas[
            df_visitas["Protocolo"].fillna("").astype(str).str.strip() == protocolo_sel
        ]
        for _, row in df_visitas_filtrado.iterrows():
            periodo = normalizar_texto_campo(row.get("Periodo/visita"))
            brazo = normalizar_texto_campo(row.get("Brazo/parte"))
            frecuencia = normalizar_texto_campo(row.get("Frecuencia/ventana"))
            procedimientos = normalizar_texto_campo(row.get("Procedimientos / pruebas"))
            laboratorios = normalizar_texto_campo(row.get("Laboratorios en esa visita"))

            partes = [f"Visita: {periodo or 'Sin especificar'}"]
            if brazo:
                partes.append(f"Brazo/parte: {brazo}")
            if frecuencia:
                partes.append(f"Ventana: {frecuencia}")
            if procedimientos:
                partes.append(f"Procedimientos: {procedimientos}")
            if laboratorios:
                partes.append(f"Laboratorios: {laboratorios}")
            items.append(" | ".join(partes))

    df_analitos = hojas_excel.get("Analitos")
    if df_analitos is not None and not df_analitos.empty and "Protocolo" in df_analitos.columns:
        df_analitos_filtrado = df_analitos[
            df_analitos["Protocolo"].fillna("").astype(str).str.strip() == protocolo_sel
        ]
        for _, row in df_analitos_filtrado.iterrows():
            panel = normalizar_texto_campo(row.get("Panel"))
            analitos = normalizar_texto_campo(row.get("Analitos / parámetros"))

            partes = [f"Panel analítico: {panel or 'Sin especificar'}"]
            if analitos:
                partes.append(f"Analitos/parámetros: {analitos}")
            items.append(" | ".join(partes))

    items_unicos = []
    vistos = set()
    for item in items:
        clave = item.casefold()
        if clave in vistos:
            continue
        vistos.add(clave)
        items_unicos.append(item)

    return items_unicos


@st.cache_data(show_spinner=False)
def resumir_checklist_excel_desde_bytes(bytes_excel):
    hojas_excel = cargar_excel_desde_bytes(bytes_excel)
    protocolos = _listar_protocolos_checklist(hojas_excel)
    items_por_protocolo = {
        protocolo: _construir_items_protocolo_desde_excel(hojas_excel, protocolo)
        for protocolo in protocolos
    }
    return protocolos, items_por_protocolo


def clasificar_item_checklist(item):
    txt = normalizar_texto_campo(item).lower()
    if txt.startswith("visita:"):
        return "Visitas"
    if txt.startswith("panel analítico:") or txt.startswith("panel analitico:"):
        return "Analitos"
    return "Otros"


def descomponer_item_checklist(item):
    texto = normalizar_texto_campo(item)
    if not texto:
        return "General", "", ""

    if texto.startswith("Visita:"):
        resto = texto.split(":", 1)[1].strip()
        partes = [p.strip() for p in resto.split("|") if p.strip()]
        titulo = partes[0] if partes else "Visita"
        detalle = " | ".join(partes[1:]) if len(partes) > 1 else ""
        return "Visitas", titulo, detalle

    if texto.startswith("Panel analítico:") or texto.startswith("Panel analitico:"):
        resto = texto.split(":", 1)[1].strip()
        partes = [p.strip() for p in resto.split("|") if p.strip()]
        titulo = partes[0] if partes else "Panel"
        detalle = " | ".join(partes[1:]) if len(partes) > 1 else ""
        return "Analitos", titulo, detalle

    if ":" in texto:
        grupo, resto = texto.split(":", 1)
        return normalizar_texto_campo(grupo) or "General", normalizar_texto_campo(resto), ""

    return "General", texto, ""


def agrupar_items_checklist(df_items):
    grupos = []
    mapa_indices = {}

    for _, row in df_items.iterrows():
        grupo, titulo, detalle = descomponer_item_checklist(row["item"])
        if grupo not in mapa_indices:
            mapa_indices[grupo] = len(grupos)
            grupos.append({"grupo": grupo, "items": []})

        grupos[mapa_indices[grupo]]["items"].append(
            {
                "id": int(row["id"]),
                "titulo": titulo or normalizar_texto_campo(row["item"]),
                "detalle": detalle,
                "done": bool(row["done"]),
                "item": row["item"],
            }
        )

    return grupos


def _buscar_columna_por_patron(df, patrones):
    columnas = list(df.columns)
    if not columnas:
        return None

    for patron in patrones:
        for col in columnas:
            col_txt = str(col).strip().lower()
            if re.search(patron, col_txt):
                return col
    return None


def _detectar_columna_fecha(df):
    if df.empty:
        return None

    prioridad = [r"fecha", r"date", r"dia", r"día"]
    candidatas = []

    for col in df.columns:
        col_txt = str(col).strip().lower()
        if any(re.search(p, col_txt) for p in prioridad):
            candidatas.append(col)

    if not candidatas:
        candidatas = list(df.columns)

    mejor_col = None
    mejor_score = 0
    for col in candidatas:
        serie_fecha = _convertir_serie_a_fecha_excel(df[col])
        score = int(serie_fecha.notna().sum())
        if score > mejor_score:
            mejor_score = score
            mejor_col = col

    if mejor_score == 0:
        return None
    return mejor_col


def _detectar_fechas_en_encabezados(df):
    columnas_fecha = []
    for col in df.columns:
        dt = _convertir_valor_a_fecha_excel(col)
        if pd.notna(dt):
            columnas_fecha.append((col, dt.date().isoformat()))
    return columnas_fecha


def _convertir_serie_a_fecha_excel(serie):
    numerico = pd.to_numeric(serie, errors="coerce")
    fecha_texto = pd.to_datetime(serie, errors="coerce", dayfirst=True)
    fecha_serial = pd.to_datetime(numerico, unit="D", origin="1899-12-30", errors="coerce")

    resultado = fecha_texto.copy()
    mascara_excel_serial = numerico.notna() & numerico.between(20000, 80000)
    if hasattr(resultado, "loc"):
        resultado.loc[mascara_excel_serial] = fecha_serial.loc[mascara_excel_serial]
    return resultado


def _convertir_valor_a_fecha_excel(valor):
    if pd.isna(valor):
        return pd.NaT

    if isinstance(valor, (int, float)):
        if 20000 <= float(valor) <= 80000:
            return pd.to_datetime(float(valor), unit="D", origin="1899-12-30", errors="coerce")

    return pd.to_datetime(valor, errors="coerce", dayfirst=True)


def _formatear_fecha_es_sin_hora(valor):
    if pd.isna(valor):
        return ""

    dt = _convertir_valor_a_fecha_excel(valor)
    if pd.notna(dt):
        return dt.strftime("%d/%m/%Y")

    txt = str(valor or "").strip()
    if not txt or txt.lower() == "nan":
        return ""

    # Si viene como texto con hora, nos quedamos con la parte de fecha.
    if " " in txt and ":" in txt.split(" ", 1)[1]:
        txt = txt.split(" ", 1)[0].strip()

    # Intento final de parseo para devolver siempre formato español cuando sea fecha.
    dt2 = pd.to_datetime(txt, errors="coerce", dayfirst=True)
    if pd.notna(dt2):
        return dt2.strftime("%d/%m/%Y")

    return txt


def _detectar_columna_por_texto_en_hoja(df, patron):
    if df.empty:
        return None
    filas_max = min(len(df), 25)
    for i in range(filas_max):
        for j, valor in enumerate(df.iloc[i].tolist()):
            texto = str(valor).strip().lower()
            if not texto or texto == "nan":
                continue
            if re.search(patron, texto):
                return j
    return None


def _normalizar_etiqueta_excel(valor):
    txt = str(valor or "").strip().lower()
    txt = txt.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
    txt = txt.replace(" ", "")
    txt = re.sub(r"[^a-z0-9+\-]", "", txt)
    return txt


def _valor_texto_celda(valor):
    if pd.isna(valor):
        return ""
    return str(valor).strip()


def _extraer_tabla_variables_dreamm10(df):
    if df.empty:
        return pd.DataFrame(), {}

    esperadas = {"w", "week", "c", "ciclo", "fecha", "ventana+", "ventana-", "dosislena", "dosis"}
    mejor_fila = None
    mejor_score = 0
    filas_max = min(len(df), 40)

    for i in range(filas_max):
        fila = df.iloc[i].tolist()
        tokens = {_normalizar_etiqueta_excel(v) for v in fila if str(v).strip() and str(v).strip().lower() != "nan"}
        score = len(tokens.intersection(esperadas))
        if score > mejor_score:
            mejor_score = score
            mejor_fila = i

    if mejor_fila is None or mejor_score < 3:
        return pd.DataFrame(), {}

    encabezados_raw = [str(v).strip() for v in df.iloc[mejor_fila].tolist()]
    tabla = df.iloc[mejor_fila + 1 :].copy().reset_index(drop=True)
    tabla.columns = encabezados_raw
    tabla = tabla.dropna(how="all")

    mapa = {}
    for col in tabla.columns:
        token = _normalizar_etiqueta_excel(col)
        if token in {"w", "week", "semana"}:
            mapa["week"] = col
        elif token in {"c", "ciclo"}:
            mapa["ciclo"] = col
        elif token == "fecha":
            mapa["fecha"] = col
        elif token == "ventana+":
            mapa["ventana_mas"] = col
        elif token == "ventana-":
            mapa["ventana_menos"] = col
        elif token.startswith("dosis") or token in {"lenalidomida", "dosislenalidomida"}:
            mapa["dosis_lena"] = col

    return tabla, mapa


def _mapear_columnas_variables_desde_headers(df):
    mapa = {}
    for col in df.columns:
        token = _normalizar_etiqueta_excel(col)
        if token in {"w", "week", "semana"}:
            mapa["week"] = col
        elif token in {"c", "ciclo"}:
            mapa["ciclo"] = col
        elif token in {"fecha", "date"}:
            mapa["fecha"] = col
        elif token in {"ventana+", "ventanamas", "window+", "windowplus"}:
            mapa["ventana_mas"] = col
        elif token in {"ventana-", "ventanamenos", "window-", "windowminus"}:
            mapa["ventana_menos"] = col
        elif token.startswith("dosis") or token in {"lenalidomida", "dosislenalidomida"}:
            mapa["dosis_lena"] = col
    return mapa


def _celda_indica_visita(valor):
    if pd.isna(valor):
        return False

    if isinstance(valor, (int, float)):
        return float(valor) != 0.0

    txt = str(valor).strip().lower()
    if not txt:
        return False
    if txt in {"0", "no", "nan", "none", "false", "-"}:
        return False
    return True


def construir_eventos_calendario_dreamm10(
    df,
    nombre_hoja="",
    modo_fecha="Auto",
    col_fecha_forzada=None,
):
    if df.empty:
        return []

    col_codigo = _buscar_columna_por_patron(df, [r"codigo", r"paciente", r"nombre", r"id"])
    col_ciclo = _buscar_columna_por_patron(df, [r"ciclo", r"visit", r"dia", r"día", r"day"])

    eventos = []

    def _titulo_base(row):
        piezas = ["DREAMM10"]
        if col_codigo is not None:
            codigo = str(row.get(col_codigo, "")).strip()
            if codigo and codigo.lower() != "nan":
                piezas.append(codigo)
        if col_ciclo is not None:
            ciclo = str(row.get(col_ciclo, "")).strip()
            if ciclo and ciclo.lower() != "nan":
                piezas.append(ciclo)
        titulo_base = " | ".join(piezas)
        if nombre_hoja:
            titulo_base = f"{titulo_base} [{nombre_hoja}]"
        return titulo_base

    usar_columna_fecha = modo_fecha in {"Auto", "Columna fecha"}
    usar_fechas_encabezado = modo_fecha in {"Auto", "Encabezados con fecha"}

    if usar_columna_fecha:
        col_fecha = col_fecha_forzada or _detectar_columna_fecha(df)
        if col_fecha is not None:
            trabajo = df.copy()
            trabajo["__fecha__"] = pd.to_datetime(trabajo[col_fecha], errors="coerce", dayfirst=True)
            trabajo = trabajo[trabajo["__fecha__"].notna()].copy()

            for _, row in trabajo.iterrows():
                eventos.append(
                    {
                        "title": _titulo_base(row),
                        "start": row["__fecha__"].date().isoformat(),
                        "allDay": True,
                        "backgroundColor": "#0ea5e9",
                        "borderColor": "#0369a1",
                    }
                )

    if usar_fechas_encabezado:
        cols_fecha = _detectar_fechas_en_encabezados(df)
        if cols_fecha:
            for _, row in df.iterrows():
                titulo_base = _titulo_base(row)
                for col_fecha, fecha_iso in cols_fecha:
                    valor = row.get(col_fecha)
                    if not _celda_indica_visita(valor):
                        continue
                    eventos.append(
                        {
                            "title": titulo_base,
                            "start": fecha_iso,
                            "allDay": True,
                            "backgroundColor": "#0ea5e9",
                            "borderColor": "#0369a1",
                        }
                    )

    dedupe = {}
    for ev in eventos:
        clave = f"{ev.get('start','')}|{ev.get('title','')}"
        dedupe[clave] = ev
    eventos = list(dedupe.values())

    if len(eventos) > 3000:
        eventos = eventos[:3000]

    return eventos


def diagnostico_columnas_fecha(df):
    filas = []
    for col in df.columns:
        serie_fecha = _convertir_serie_a_fecha_excel(df[col])
        score = int(serie_fecha.notna().sum())
        if score > 0:
            filas.append({"columna": str(col), "fechas_validas": score})
    if not filas:
        return pd.DataFrame(columns=["columna", "fechas_validas"])
    return pd.DataFrame(filas).sort_values(by="fechas_validas", ascending=False).reset_index(drop=True)


def construir_eventos_fallback_todas_fechas(df, nombre_hoja=""):
    if df.empty:
        return []

    eventos = []
    for idx, row in df.iterrows():
        for col in df.columns:
            valor = row.get(col)
            fecha = _convertir_valor_a_fecha_excel(valor)
            if pd.isna(fecha):
                continue
            titulo = "DREAMM10"
            if nombre_hoja:
                titulo = f"{titulo} [{nombre_hoja}]"
            titulo = f"{titulo} | fila {idx + 1}"
            eventos.append(
                {
                    "title": titulo,
                    "start": fecha.date().isoformat(),
                    "allDay": True,
                    "backgroundColor": "#0ea5e9",
                    "borderColor": "#0369a1",
                }
            )

    dedupe = {}
    for ev in eventos:
        clave = f"{ev.get('start','')}|{ev.get('title','')}"
        dedupe[clave] = ev
    eventos = list(dedupe.values())

    if len(eventos) > 3000:
        eventos = eventos[:3000]

    return eventos


def extraer_registros_visitas_dreamm10(df, nombre_hoja=""):
    if df.empty:
        return []

    registros = []
    tabla_vars = pd.DataFrame()
    mapa_vars = {}

    # 1) Formato preferente: variables ya son encabezados de columna.
    mapa_headers = _mapear_columnas_variables_desde_headers(df)
    if "fecha" in mapa_headers:
        tabla_vars = df.copy().dropna(how="all")
        mapa_vars = mapa_headers
        iterable = tabla_vars.iterrows()
        usar_tabla_vars = True
    else:
        # 2) Fallback: detectar una fila que contiene los nombres de variables.
        tabla_vars, mapa_vars = _extraer_tabla_variables_dreamm10(df)
        if not tabla_vars.empty and "fecha" in mapa_vars:
            iterable = tabla_vars.iterrows()
            usar_tabla_vars = True
        else:
            # 3) Fallback final por linea, prioridad columna C.
            iterable = df.iterrows()
            usar_tabla_vars = False

    for _, row in iterable:
        fecha_dt = pd.NaT
        valor_c = ""

        if usar_tabla_vars:
            valor_fecha_raw = row.get(mapa_vars.get("fecha"))
            valor_c_raw = row.get(mapa_vars.get("ciclo"))
            valor_c = "" if pd.isna(valor_c_raw) else str(valor_c_raw).strip()
            fecha_dt = _convertir_valor_a_fecha_excel(valor_fecha_raw)
        else:
            col_fecha_idx = 2 if len(row) > 2 else None
            if col_fecha_idx is not None:
                valor_c_raw = row.iloc[col_fecha_idx]
                valor_c = "" if pd.isna(valor_c_raw) else str(valor_c_raw).strip()
                fecha_dt = _convertir_valor_a_fecha_excel(valor_c_raw)

        if pd.isna(fecha_dt):
            for valor in row.tolist():
                fecha_test = _convertir_valor_a_fecha_excel(valor)
                if pd.notna(fecha_test):
                    fecha_dt = fecha_test
                    break

        if pd.isna(fecha_dt):
            continue

        # Cada pestaña es un paciente.
        codigo = str(nombre_hoja or "").strip()
        nombre = str(nombre_hoja or "").strip()
        ciclo = ""

        if usar_tabla_vars:
            valor_w = "" if "week" not in mapa_vars else _valor_texto_celda(row.get(mapa_vars["week"]))
            valor_c = "" if "ciclo" not in mapa_vars else _valor_texto_celda(row.get(mapa_vars["ciclo"]))
            valor_vmas = "" if "ventana_mas" not in mapa_vars else _formatear_fecha_es_sin_hora(row.get(mapa_vars["ventana_mas"]))
            valor_vmenos = "" if "ventana_menos" not in mapa_vars else _formatear_fecha_es_sin_hora(row.get(mapa_vars["ventana_menos"]))
            valor_dosis = "" if "dosis_lena" not in mapa_vars else _valor_texto_celda(row.get(mapa_vars["dosis_lena"]))
        else:
            col_w_idx = 22 if len(row) > 22 else None
            col_ventana_mas_idx = _detectar_columna_por_texto_en_hoja(df, r"ventana\s*\+")
            col_ventana_menos_idx = _detectar_columna_por_texto_en_hoja(df, r"ventana\s*-")
            valor_w = "" if col_w_idx is None else _valor_texto_celda(row.iloc[col_w_idx])
            valor_vmas = "" if col_ventana_mas_idx is None else _formatear_fecha_es_sin_hora(row.iloc[col_ventana_mas_idx])
            valor_vmenos = "" if col_ventana_menos_idx is None else _formatear_fecha_es_sin_hora(row.iloc[col_ventana_menos_idx])
            valor_dosis = ""

        partes_comentario = []
        if valor_w and valor_w.lower() != "nan":
            partes_comentario.append(f"W: {valor_w}")
        if valor_c and valor_c.lower() != "nan":
            partes_comentario.append(f"C: {valor_c}")
        if valor_vmas and valor_vmas.lower() != "nan":
            partes_comentario.append(f"Ventana +: {valor_vmas}")
        if valor_vmenos and valor_vmenos.lower() != "nan":
            partes_comentario.append(f"Ventana -: {valor_vmenos}")
        if valor_dosis and valor_dosis.lower() != "nan":
            partes_comentario.append(f"Dosis lena: {valor_dosis}")
        comentario = " | ".join(partes_comentario)
        if nombre_hoja:
            comentario = (f"Paciente (pestaña): {nombre_hoja}" + (" | " + comentario if comentario else ""))

        registros.append(
            {
                "fecha": fecha_dt.date().isoformat(),
                "codigo": codigo,
                "nombre": nombre,
                "ensayo": "DREAMM 10",
                "ciclo": ciclo,
                "w": valor_w,
                "c": valor_c,
                "dosis_lena": valor_dosis,
                "ventana_mas": valor_vmas,
                "ventana_menos": valor_vmenos,
                "comentarios": comentario,
                "origen_hoja": nombre_hoja,
            }
        )

    dedupe = {}
    for r in registros:
        clave = (
            str(r.get("fecha") or "").strip(),
            normalizar_texto_campo(r.get("codigo")),
            nombre_a_iniciales(r.get("nombre")),
            normalizar_texto_campo(r.get("ciclo")),
            normalizar_texto_campo(r.get("comentarios")),
            normalizar_texto_campo(r.get("origen_hoja")),
        )
        dedupe[clave] = r
    return list(dedupe.values())


def insertar_registros_dreamm10_en_tabla(registros):
    # DREAMM10 es una pestaña aislada: no persiste registros en la agenda general.
    if not registros:
        return 0, 0

    normalizadas = set()
    duplicados = 0
    for r in registros:
        clave = (
            str(r.get("fecha") or "").strip(),
            normalizar_texto_campo(r.get("codigo")),
            nombre_a_iniciales(r.get("nombre")),
            normalizar_ensayo(r.get("ensayo") or "DREAMM 10"),
            normalizar_texto_campo(r.get("ciclo")),
        )
        if not clave[0]:
            continue
        if clave in normalizadas:
            duplicados += 1
            continue
        normalizadas.add(clave)

    return 0, duplicados


def limpiar_arrastre_dreamm10_en_agenda():
    """Elimina de visitas los registros importados desde la pestaña DREAMM10.

    Mantiene la agenda general limpia de sincronizaciones históricas y
    reconstruye la tabla de pacientes a partir de las visitas restantes.
    """
    conn = connect_db()
    c = conn.cursor()

    filas = c.execute(
        """
        SELECT id, ensayo, comentarios
        FROM visitas
        """,
    ).fetchall()

    ids_borrar = [
        int(fila_id)
        for (fila_id, ensayo, comentarios) in filas
        if es_visita_importada_dreamm10(ensayo, comentarios)
    ]

    if not ids_borrar:
        conn.close()
        return 0

    placeholders = ",".join(["?"] * len(ids_borrar))
    c.execute(f"DELETE FROM revision_ocular WHERE visita_id IN ({placeholders})", tuple(ids_borrar))
    c.execute(f"DELETE FROM visitas WHERE id IN ({placeholders})", tuple(ids_borrar))

    sincronizar_pacientes_desde_visitas(c)
    eliminar_ensayos_sin_pacientes(c)
    conn.commit()
    conn.close()

    invalidar_cache_lecturas()
    snapshot_db("pacientes")
    return len(ids_borrar)


def construir_eventos_desde_registros_dreamm10(registros):
    eventos = []
    for idx, r in enumerate(registros):
        fecha = str(r.get("fecha") or "").strip()
        if not fecha:
            continue

        codigo = str(r.get("codigo") or "").strip()
        nombre = str(r.get("nombre") or "").strip()
        week = str(r.get("w") or "").strip()
        ciclo = str(r.get("c") or "").strip()
        dosis = str(r.get("dosis_lena") or "").strip()
        detalle = str(r.get("comentarios") or "").strip()

        paciente_visible = nombre or codigo or "Paciente"
        week_visible = week or "-"
        ciclo_visible = ciclo or "-"
        dosis_visible = dosis or "-"
        titulo = f"{paciente_visible} | W {week_visible} | C {ciclo_visible} | D {dosis_visible}"

        eventos.append(
            {
                "id": str(idx),
                "title": titulo,
                "start": fecha,
                "allDay": True,
                "extendedProps": {
                    "registro_idx": idx,
                    "paciente": nombre,
                    "codigo": codigo,
                    "week": week,
                    "ciclo": ciclo,
                    "dosis_lena": dosis,
                    "ventana_mas": str(r.get("ventana_mas") or "").strip(),
                    "ventana_menos": str(r.get("ventana_menos") or "").strip(),
                    "contenido": detalle,
                    "origen_hoja": str(r.get("origen_hoja") or "").strip(),
                    "fecha": fecha,
                },
                "backgroundColor": "#0ea5e9",
                "borderColor": "#0369a1",
            }
        )

    dedupe = {}
    for ev in eventos:
        clave = f"{ev.get('start','')}|{ev.get('title','')}"
        dedupe[clave] = ev
    eventos = list(dedupe.values())

    if len(eventos) > 3000:
        eventos = eventos[:3000]

    return eventos


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
        df_manana["fecha_evaluacion"] = None
        df_manana["resultado"] = None
        df_manana["sede"] = None
        df_manana["agenda_hospitalaria"] = None

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

        fecha_rev = parse_fecha_iso(row.get("fecha_evaluacion")) if "fecha_evaluacion" in row else None
        resultado_rev = "" if pd.isna(row.get("resultado")) else str(row.get("resultado")).strip()
        sede_rev = "" if pd.isna(row.get("sede")) else str(row.get("sede")).strip()
        agenda_hosp = "" if pd.isna(row.get("agenda_hospitalaria")) else str(row.get("agenda_hospitalaria")).strip()
        if fecha_rev:
            detalle_rev = f"Revisión ocular: {fecha_rev.strftime('%d/%m/%Y')}"
            if sede_rev:
                detalle_rev += f" ({sede_rev.title()})"
            tareas.append(detalle_rev)
        if resultado_rev:
            tareas.append(f"Resultado ocular: {resultado_rev}")
        if agenda_hosp:
            tareas.append(f"Agenda hospitalaria (ojos): {agenda_hosp}")

        comentarios = "" if pd.isna(row.get("comentarios")) else str(row.get("comentarios")).strip()
        if comentarios:
            tareas.append(f"Comentarios: {comentarios}")

        if not tareas:
            tareas.append("Sin tareas adicionales registradas")

        titulo = f"🆔 {codigo} | {nombre} | {ensayo}".strip(" |")
        with st.expander(titulo, expanded=True):
            for tarea in tareas:
                st.write(f"• {tarea}")


def renderizar_registro_kits_integrado():
    ruta_kits = os.path.join(SCRIPT_DIR, "inventario_kits_app.py")
    if not os.path.isfile(ruta_kits):
        st.error("No se encuentra el modulo de registro de kits en el servidor.")
        return

    set_page_config_original = st.set_page_config
    try:
        # El modulo de kits tambien se ejecuta standalone y configura pagina.
        # Al integrarlo dentro de la app principal anulamos esa llamada.
        st.set_page_config = lambda *args, **kwargs: None
        runpy.run_path(ruta_kits, run_name="__kits_integrado__")
    except Exception as exc:
        st.error(f"No se pudo cargar la pestaña de kits: {exc}")
    finally:
        st.set_page_config = set_page_config_original


def render_interfaz_medica():
    st.subheader("Interfaz medica")

    st.markdown(
        """
        <style>
            .block-container {padding-top: 0.4rem !important; padding-bottom: 0.35rem !important; max-width: 1200px !important;}
            [data-testid="stVerticalBlock"] > [style*="flex-direction: column"] > [data-testid="stVerticalBlock"] {gap: 0.15rem !important;}
            h3, h4 {margin-top: 0.08rem !important; margin-bottom: 0.12rem !important; font-size: 0.95rem !important;}
            div[data-testid="stCheckbox"] {
                background: #edf1f6;
                border: 1px solid #d6deea;
                border-radius: 8px;
                padding: 2px 5px;
                margin-bottom: 2px;
            }
            div[data-testid="stCheckbox"] label p {
                color: #415271 !important;
                font-weight: 700 !important;
                font-size: 0.88rem !important;
                margin: 0 !important;
            }
            div[data-testid="stCheckbox"]:has(input:checked) {
                background: linear-gradient(135deg, #0f4aa6, #0a68c7);
                border-color: #0f4aa6;
                box-shadow: 0 3px 8px rgba(15, 74, 166, 0.18);
            }
            div[data-testid="stCheckbox"]:has(input:checked) label p {
                color: #ffffff !important;
            }
            .im-shell {background: linear-gradient(160deg, #ffffff 0%, #f5f9ff 58%, #f2fbf5 100%); border: 1px solid #d7e2f3; border-radius: 12px; box-shadow: 0 6px 14px rgba(18,50,94,0.05); padding: 6px 8px; margin-bottom: 3px;}
            .im-top {display: flex; align-items: center; gap: 5px; margin-bottom: 2px;}
            .im-avatar {width: 26px; height: 26px; border-radius: 50%; display:flex; align-items:center; justify-content:center; background: linear-gradient(135deg, #dbe9ff, #c8f3e1); border: 1px solid #c4d9ff; color: #1f3b66; font-size: 0.8rem; font-weight: 700;}
            .im-title {font-size: 0.95rem; font-weight: 800; color: #22314a; margin-bottom: 0; line-height: 1.05;}
            .im-sub {font-size: 0.8rem; color: #55729a; margin-bottom: 0; line-height: 1.08;}
            .im-banner {border-radius: 8px; padding: 4px 6px; font-size: 0.8rem; font-weight: 700; margin-top: 2px; border: 1px solid #d6e3f8;}
            .im-chip {padding: 4px 8px; border-radius: 999px; border: 1px solid #d5def0; font-size: 0.73rem; color: #4b5d7f; background: #ffffff;}
            .im-chip-active {padding: 4px 8px; border-radius: 999px; border: 1px solid #0f4aa6; font-size: 0.73rem; color: #ffffff; background: linear-gradient(90deg, #0f4aa6, #0a68c7);}
            .im-mini-card {border: 1px solid #d9e4f4; background: #ffffff; border-radius: 12px; padding: 8px 10px; margin-bottom: 7px; font-size: 0.86rem; color: #2b3a54;}
            .im-ok {border-left: 4px solid #1b9f66;}
            .im-warn {border-left: 4px solid #db6a1a;}
            .im-danger {border-left: 4px solid #c0392b;}
            [data-testid="stWidgetLabel"] p,
            .stTextInput label,
            .stTextArea label,
            .stSelectbox label,
            .stDateInput label,
            .stMultiSelect label,
            .stRadio label {
                font-size: 0.92rem !important;
                font-weight: 700 !important;
                margin: 0 !important;
            }
            .stTextInput input,
            .stTextArea textarea,
            .stDateInput input,
            .stSelectbox div[data-baseweb="select"] input {
                font-size: 0.9rem !important;
            }
            .stCaption {font-size: 0.75rem !important; margin: 1px 0 !important;}
        </style>
        """,
        unsafe_allow_html=True,
    )

    df_visitas = get_visitas()
    if df_visitas.empty:
        st.info("No hay visitas registradas para mostrar la interfaz medica.")
        return

    df_visitas = df_visitas.copy()
    df_visitas["ensayo"] = df_visitas["ensayo"].fillna("").astype(str)
    df_visitas["codigo"] = df_visitas["codigo"].fillna("").astype(str)
    df_visitas["nombre"] = df_visitas["nombre"].fillna("").astype(str)
    df_visitas["fecha"] = df_visitas["fecha"].fillna("").astype(str)
    df_visitas["_fecha_dt"] = pd.to_datetime(df_visitas["fecha"], errors="coerce")

    # Usamos la misma fuente que Agenda: eventos del calendario.
    eventos_agenda = construir_eventos_calendario(df_visitas)
    ids_por_fecha = {}
    for ev in eventos_agenda:
        props = ev.get("extendedProps") or {}
        visita_id = props.get("id")
        if visita_id in (None, ""):
            # Ignoramos eventos teóricos sin visita real.
            continue
        fecha_raw = str(ev.get("start") or "").strip()
        fecha_txt = fecha_raw[:10]
        fecha_dt = parse_fecha_iso(fecha_txt)
        if not fecha_dt:
            continue
        ids_por_fecha.setdefault(fecha_dt, set()).add(int(visita_id))

    if not ids_por_fecha:
        st.warning("No hay pacientes en el calendario de Agenda para mostrar en Interfaz medica.")
        return

    fechas_disponibles = sorted(ids_por_fecha.keys(), reverse=True)
    hoy = fecha_hoy_local()
    idx_hoy = fechas_disponibles.index(hoy) if hoy in fechas_disponibles else 0
    key_idx = "im_fecha_idx"
    if key_idx not in st.session_state:
        st.session_state[key_idx] = idx_hoy
    st.session_state[key_idx] = max(0, min(int(st.session_state[key_idx]), len(fechas_disponibles) - 1))

    fecha_sel = fechas_disponibles[st.session_state[key_idx]]

    # Barra de navegación de día con date_input + botones
    dc1, dc2, dc3, dc4 = st.columns([0.28, 1.8, 0.55, 0.28])
    if dc1.button("◀", key="im_dia_ant"):
        st.session_state[key_idx] = min(len(fechas_disponibles) - 1, st.session_state[key_idx] + 1)
        st.rerun()
    fecha_picker = dc2.date_input(
        "Dia",
        value=fecha_sel,
        min_value=min(fechas_disponibles),
        max_value=max(fechas_disponibles),
        key="im_fecha_picker",
        label_visibility="collapsed",
    )
    if fecha_picker != fecha_sel:
        if fecha_picker in fechas_disponibles:
            st.session_state[key_idx] = fechas_disponibles.index(fecha_picker)
        else:
            # Encuentra el día disponible más cercano
            import bisect
            fechas_asc = sorted(fechas_disponibles)
            pos = bisect.bisect_left(fechas_asc, fecha_picker)
            pos = min(pos, len(fechas_asc) - 1)
            st.session_state[key_idx] = fechas_disponibles.index(fechas_asc[pos])
        st.rerun()
    if dc3.button("Hoy", key="im_fecha_hoy"):
        st.session_state[key_idx] = idx_hoy
        st.rerun()
    if dc4.button("▶", key="im_dia_sig"):
        st.session_state[key_idx] = max(0, st.session_state[key_idx] - 1)
        st.rerun()

    ids_dia = ids_por_fecha.get(fecha_sel, set())
    df_fil = df_visitas[df_visitas["id"].apply(lambda v: int(v) in ids_dia if pd.notna(v) else False)].copy()
    df_fil = df_fil.sort_values(by=["ensayo", "codigo", "nombre", "id"], na_position="last")

    pacientes_map = {}
    opciones_paciente = []
    for _, row in df_fil[["codigo", "nombre", "ensayo"]].drop_duplicates().iterrows():
        cod = str(row.get("codigo", "") or "").strip()
        nom = str(row.get("nombre", "") or "").strip()
        ens = str(row.get("ensayo", "") or "").strip()
        etiqueta = f"{cod} | {nom} | {ens}".strip(" |")
        if etiqueta and etiqueta not in pacientes_map:
            pacientes_map[etiqueta] = (cod, nom, ens)
            opciones_paciente.append(etiqueta)

    if not opciones_paciente:
        st.warning("No hay pacientes para la fecha seleccionada.")
        return

    # Fila de iconos de paciente: silueta + ciclo, clic para seleccionar
    pac_sel_key = "im_pac_sel"
    if pac_sel_key not in st.session_state or st.session_state[pac_sel_key] not in opciones_paciente:
        st.session_state[pac_sel_key] = opciones_paciente[0]
    paciente_sel = st.session_state[pac_sel_key]

    pac_cols = st.columns(len(opciones_paciente))
    for i, etiqueta in enumerate(opciones_paciente):
        cod_i, nom_i, ens_i = pacientes_map[etiqueta]
        sexo_i = _inferir_sexo(nom_i)
        svg_i = _SVG_SILUETA_F if sexo_i == "F" else _SVG_SILUETA_M
        df_pac_i = df_fil[
            df_fil["codigo"].str.strip().str.casefold() == cod_i.casefold()
        ] if cod_i else df_fil[df_fil["nombre"].str.strip().str.casefold() == nom_i.casefold()]
        ciclo_i = str(df_pac_i.iloc[0].get("ciclo", "") if not df_pac_i.empty else "") or "-"
        iniciales_i = "".join([t[0] for t in nom_i.split()[:2]]).upper() if nom_i else cod_i[:2].upper()
        is_sel = (etiqueta == paciente_sel)
        color_sil = "#0f4aa6" if is_sel else "#7a9cc4"
        bg = "#dbeafe" if is_sel else "#f0f4fa"
        border = "2px solid #0f4aa6" if is_sel else "1px solid #d6deea"
        with pac_cols[i]:
            # Silueta SVG encima, no interactiva
            st.markdown(
                f'<div style="text-align:center;color:{color_sil};width:26px;margin:0 auto 2px auto">{svg_i}</div>',
                unsafe_allow_html=True,
            )
            # Botón real con iniciales + ciclo, estilizado como tarjeta
            btn_label = f"{iniciales_i}\n{ciclo_i}"
            if st.button(
                btn_label,
                key=f"im_pac_{i}",
                use_container_width=True,
                type="primary" if is_sel else "secondary",
            ):
                st.session_state[pac_sel_key] = etiqueta
                st.rerun()

    cod_sel, nom_sel, ens_sel = pacientes_map[paciente_sel]

    cod_norm = normalizar_clave_paciente(cod_sel)
    nom_norm = normalizar_clave_paciente(nom_sel)
    ens_norm = normalizar_clave_paciente(ens_sel)

    mask = df_fil["ensayo"].apply(normalizar_clave_paciente) == ens_norm
    if cod_norm:
        mask = mask & (df_fil["codigo"].apply(normalizar_clave_paciente) == cod_norm)
    else:
        mask = mask & (df_fil["nombre"].apply(normalizar_clave_paciente) == nom_norm)

    df_paciente_visitas = df_fil[mask].sort_values(by=["_fecha_dt", "id"], ascending=[False, False]).copy()
    if df_paciente_visitas.empty:
        st.warning("No se encontraron visitas para este paciente.")
        return

    opciones_visita = []
    mapa_visitas = {}
    for _, row in df_paciente_visitas.iterrows():
        visita_id = int(row["id"])
        fecha_txt = formatear_fecha_visita(row.get("fecha"))
        ciclo_txt = str(row.get("ciclo", "") or "").strip() or "Sin ciclo"
        etiqueta = f"Visita #{visita_id} | {fecha_txt} | {ciclo_txt}"
        opciones_visita.append(etiqueta)
        mapa_visitas[etiqueta] = row.to_dict()

    if len(opciones_visita) == 1:
        visita_sel = opciones_visita[0]
    else:
        visita_sel = st.selectbox("Visita", options=opciones_visita, key="im_visita")
    visita_row = mapa_visitas[visita_sel]
    visita_id = int(visita_row["id"])
    fecha_visita_txt = formatear_fecha_visita(visita_row.get("fecha"))
    fecha_agenda_txt = fecha_sel.strftime("%d/%m/%Y")
    fecha_real_hoy_txt = fecha_hoy_local().strftime("%d/%m/%Y")

    estado = get_estado_interfaz_medica(visita_row)

    pasos = [
        "Resumen de visita",
        "Constantes y parametros",
        "Comentarios del paciente",
        "Pruebas a realizar",
        "Farmacos de estudio",
        "Medicacion concomitante",
        "Efectos adversos",
        "Decision de tratamiento",
        "Confirmacion",
        "Historia clinica generada",
        "Mas informacion",
    ]
    step_key = f"im_step_{visita_id}"
    if step_key not in st.session_state:
        st.session_state[step_key] = 1
    paso = int(st.session_state[step_key])
    paso = max(1, min(len(pasos), paso))
    st.session_state[step_key] = paso

    iconos = ["R", "V", "C", "P", "F", "M", "AE", "D", "OK", "N", "I"]
    color_paso = {
        1: "#0f4aa6",
        2: "#0f8b5f",
        3: "#5f3dc4",
        4: "#4f46e5",
        5: "#0f8b5f",
        6: "#265ea8",
        7: "#c0392b",
        8: "#db6a1a",
        9: "#1f8f62",
        10: "#db6a1a",
        11: "#2f3e63",
    }

    nombre_pac = str(visita_row.get("nombre", "") or "").strip()
    sexo_pac = _inferir_sexo(nombre_pac)
    svgsilhouette = _SVG_SILUETA_F if sexo_pac == "F" else _SVG_SILUETA_M
    silueta_color = "#b0c8e8" if sexo_pac == "F" else "#93b8dc"

    color_actual = color_paso.get(paso, "#0f4aa6")

    def _lista_unica_texto(items):
        vistos = set()
        salida = []
        for item in items or []:
            txt = str(item or "").strip()
            if not txt:
                continue
            clave = txt.casefold()
            if clave in vistos:
                continue
            vistos.add(clave)
            salida.append(txt)
        return salida

    def _render_checklist_onoff(titulo, estado_dict, campo, base_ops, extra_ops, clave_ui, columnas=3):
        st.markdown(f"**{titulo}**")
        ext_key = f"{campo}_expandido"
        custom_key = f"{campo}_custom"

        estado_dict[campo] = _lista_unica_texto(estado_dict.get(campo, []))
        estado_dict[custom_key] = _lista_unica_texto(estado_dict.get(custom_key, []))

        if ext_key not in estado_dict:
            estado_dict[ext_key] = False

        acciones = st.columns([1.15, 1.25, 2.6])
        if acciones[0].button("Generar mas", key=f"im_gen_{clave_ui}_{visita_id}"):
            estado_dict[ext_key] = True
        if acciones[1].button("Quitar todo", key=f"im_clear_{clave_ui}_{visita_id}"):
            estado_dict[campo] = []

        nuevas_op = acciones[2].text_input("", placeholder="Nueva opcion", key=f"im_new_{clave_ui}_{visita_id}", label_visibility="collapsed")
        if acciones[2].button("Anadir", key=f"im_add_{clave_ui}_{visita_id}"):
            nueva = str(nuevas_op or "").strip()
            if nueva:
                if nueva.casefold() not in {x.casefold() for x in estado_dict[custom_key]}:
                    estado_dict[custom_key].append(nueva)
                if nueva.casefold() not in {x.casefold() for x in estado_dict[campo]}:
                    estado_dict[campo].append(nueva)

        opciones = _lista_unica_texto(base_ops)
        if estado_dict.get(ext_key):
            opciones = _lista_unica_texto(opciones + list(extra_ops or []))
        opciones = _lista_unica_texto(opciones + estado_dict.get(custom_key, []))

        seleccion = list(estado_dict.get(campo, []))
        seleccion_set = {x.casefold() for x in seleccion}
        cols = st.columns(columnas)
        for idx, item in enumerate(opciones):
            marcado = item.casefold() in seleccion_set
            nuevo_estado = cols[idx % columnas].checkbox(item, value=marcado, key=f"im_onoff_{clave_ui}_{visita_id}_{idx}")
            if nuevo_estado and item.casefold() not in seleccion_set:
                seleccion.append(item)
                seleccion_set.add(item.casefold())
            if not nuevo_estado and item.casefold() in seleccion_set:
                seleccion = [x for x in seleccion if x.casefold() != item.casefold()]
                seleccion_set = {x.casefold() for x in seleccion}

        estado_dict[campo] = _lista_unica_texto(seleccion)
        st.caption(f"{len(estado_dict[campo])} seleccionada(s)")
        return estado_dict[campo]

    st.markdown(
        f"""
        <div class=\"im-shell\" style=\"display:flex;align-items:center;justify-content:space-between;gap:6px;\">
            <div style=\"flex:1;min-width:0;\">
                <div class=\"im-top\">
                    <div>
                        <div class=\"im-title\">{html.escape(nombre_pac or 'Paciente')}</div>
                        <div class=\"im-sub\">{html.escape(str(visita_row.get('codigo', '') or '-'))} · {html.escape(str(visita_row.get('ensayo', '') or '-'))} · Ciclo {html.escape(str(visita_row.get('ciclo', '') or '-'))}</div>
                    </div>
                </div>
                <div class=\"im-banner\" style=\"background:{color_actual}12; color:{color_actual}; border-color:{color_actual}55;\">{html.escape(iconos[paso-1])} · Paso {paso}/{len(pasos)} · {html.escape(pasos[paso-1])} · Agenda {html.escape(fecha_agenda_txt)}</div>
            </div>
            <div style=\"color:{silueta_color};width:38px;flex-shrink:0;opacity:0.85;\">{svgsilhouette}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Barra de navegación rápida entre pasos
    step_cols = st.columns(len(pasos))
    for si, (ico, nombre_paso) in enumerate(zip(iconos, pasos)):
        num = si + 1
        with step_cols[si]:
            if st.button(
                ico,
                key=f"im_quickstep_{visita_id}_{num}",
                use_container_width=True,
                type="primary" if paso == num else "secondary",
                help=nombre_paso,
            ):
                guardar_estado_interfaz_medica(visita_id, estado)
                st.session_state[step_key] = num
                st.rerun()

    completadas = 0
    if estado.get("estado_constantes", {}).get("tension_arterial"):
        completadas += 1
    if estado.get("estado_comentarios", {}).get("comentario_libre"):
        completadas += 1
    if estado.get("estado_pruebas", {}).get("pruebas"):
        completadas += 1
    if estado.get("estado_farmacos_estudio", {}).get("farmacos"):
        completadas += 1
    if estado.get("estado_medicacion_concomitante", {}).get("medicaciones"):
        completadas += 1
    if estado.get("estado_aes", {}).get("eventos"):
        completadas += 1
    if estado.get("estado_decision", {}).get("decision", "") != "Pendiente":
        completadas += 1

    if paso == 1:
        prev_row, prev_estado = _get_estado_visita_anterior(df_visitas, visita_row)
        st.markdown("**Visita anterior**")
        if prev_row is None or prev_estado is None:
            st.caption("Sin visitas previas registradas.")
        else:
            fecha_prev = formatear_fecha_visita(prev_row.get("fecha"))
            ciclo_prev = str(prev_row.get("ciclo", "") or "-")
            c_prev = prev_estado.get("estado_constantes", {})
            com_prev = prev_estado.get("estado_comentarios", {})
            ae_prev = prev_estado.get("estado_aes", {}).get("eventos", [])
            dec_prev = prev_estado.get("estado_decision", {}).get("decision", "Pendiente")
            sint_prev = com_prev.get("sintomas", [])
            st.markdown(
                f"<div class='im-mini-card im-ok' style='font-size:0.8rem;padding:5px 7px;'>"
                f"<b>{ciclo_prev}</b> · {fecha_prev}<br>"
                f"TA {c_prev.get('tension_arterial','-')} · FC {c_prev.get('fc','-')} · "
                f"Peso {c_prev.get('peso','-')} kg · SatO2 {c_prev.get('sat_o2','-')}<br>"
                f"Síntomas: {', '.join(sint_prev) if sint_prev else 'ninguno'}<br>"
                f"AEs: {len(ae_prev)} · Decisión: {html.escape(dec_prev)}"
                f"</div>",
                unsafe_allow_html=True,
            )

    if paso == 2:
        st.markdown("#### Constantes y parametros")
        c = estado["estado_constantes"]
        a1, a2, a3 = st.columns(3)
        c["tension_arterial"] = a1.text_input("Tension arterial", value=str(c.get("tension_arterial", "")), key=f"im_ta_{visita_id}")
        c["fc"] = a2.text_input("Frecuencia cardiaca", value=str(c.get("fc", "")), key=f"im_fc_{visita_id}")
        c["fr"] = a3.text_input("Frecuencia respiratoria", value=str(c.get("fr", "")), key=f"im_fr_{visita_id}")
        b1, b2, b3 = st.columns(3)
        c["temperatura"] = b1.text_input("Temperatura", value=str(c.get("temperatura", "")), key=f"im_temp_{visita_id}")
        c["sat_o2"] = b2.text_input("Saturacion O2", value=str(c.get("sat_o2", "")), key=f"im_sato2_{visita_id}")
        c["peso"] = b3.text_input("Peso (kg)", value=str(c.get("peso", "")), key=f"im_peso_{visita_id}")
        d1, d2, d3 = st.columns(3)
        c["talla"] = d1.text_input("Talla (cm)", value=str(c.get("talla", "")), key=f"im_talla_{visita_id}")
        c["imc"] = d2.text_input("IMC", value=str(c.get("imc", "")), key=f"im_imc_{visita_id}")
        c["superficie_corporal"] = d3.text_input("Superficie corporal", value=str(c.get("superficie_corporal", "")), key=f"im_sc_{visita_id}")

    if paso == 3:
        st.markdown("#### Comentarios del paciente")
        sintomas_base = [
            "Astenia/fatiga",
            "Dolor oseo",
            "Dolor neuropatico",
            "Fiebre",
            "Disnea",
            "Tos",
            "Nauseas",
            "Diarrea",
            "Estrenimiento",
            "Perdida de apetito",
            "Edema",
            "Sangrado/moretones",
        ]
        sintomas_extra = [
            "Prurito",
            "Mucositis",
            "Infecciones respiratorias",
            "Mareo",
            "Perdida de peso",
            "Dolor abdominal",
            "Cefalea",
            "Insomnio",
        ]
        com = estado["estado_comentarios"]
        com["sintomas"] = _render_checklist_onoff(
            "Sintomas referidos",
            com,
            "sintomas",
            sintomas_base,
            sintomas_extra,
            "sintomas",
            columnas=4,
        )
        com["comentario_libre"] = st.text_area(
            "Comentario libre",
            value=str(com.get("comentario_libre", "")),
            height=55,
            key=f"im_comentario_{visita_id}",
        )
        com["estado_general"] = st.selectbox(
            "Estado general",
            options=["", "ECOG 0 - Asintomatico", "ECOG 1 - Restriccion leve", "ECOG 2 - Restriccion moderada", "ECOG 3 - Limitado"],
            index=["", "ECOG 0 - Asintomatico", "ECOG 1 - Restriccion leve", "ECOG 2 - Restriccion moderada", "ECOG 3 - Limitado"].index(str(com.get("estado_general", "")) if str(com.get("estado_general", "")) in ["", "ECOG 0 - Asintomatico", "ECOG 1 - Restriccion leve", "ECOG 2 - Restriccion moderada", "ECOG 3 - Limitado"] else ""),
            key=f"im_estado_general_{visita_id}",
        )

    if paso == 4:
        st.markdown("#### Pruebas a realizar")
        pruebas = estado["estado_pruebas"]
        pruebas_base = [
            "Hemograma completo",
            "Bioquimica basica",
            "Perfil renal y hepatica",
            "LDH",
            "Beta-2 microglobulina",
            "Proteinograma",
            "Inmunofijacion suero",
            "Cadenas ligeras libres",
            "Calcio",
            "Creatinina",
        ]
        pruebas_extra = [
            "Inmunofijacion orina 24h",
            "Cuantificacion de inmunoglobulinas",
            "Aspirado/biopsia medula osea",
            "Citometria de flujo",
            "FISH/citogenetica",
            "PET-TC",
            "RMN columna",
            "ECOG Performance Status",
            "Serologias",
            "Coagulacion",
        ]
        pruebas["pruebas"] = _render_checklist_onoff(
            "Listado de pruebas",
            pruebas,
            "pruebas",
            pruebas_base,
            pruebas_extra,
            "pruebas",
            columnas=3,
        )
        for item in pruebas["pruebas"]:
            st.markdown(f"<div class='im-mini-card im-ok'>{html.escape(item)}</div>", unsafe_allow_html=True)

    if paso == 5:
        st.markdown("#### Farmacos de estudio")
        far = estado["estado_farmacos_estudio"]
        far_txt = st.text_area(
            "Farmacos (una linea por farmaco con dosis)",
            value="\n".join(far.get("farmacos", [])),
            height=78,
            key=f"im_farmacos_{visita_id}",
        )
        far["farmacos"] = [p.strip() for p in far_txt.split("\n") if p.strip()]
        for item in far["farmacos"]:
            st.markdown(f"<div class='im-mini-card im-ok'>{html.escape(item)}</div>", unsafe_allow_html=True)

    if paso == 6:
        st.markdown("#### Medicacion concomitante")
        med = estado["estado_medicacion_concomitante"]
        med_base = [
            "Aciclovir profilaxis",
            "Cotrimoxazol profilaxis",
            "Omeprazol",
            "Alopurinol",
            "Ondansetron",
            "Paracetamol",
            "Loperamida",
            "Calcio + vitamina D",
            "Bifosfonato (zoledronato)",
            "Heparina profilactica",
        ]
        med_extra = [
            "Levofloxacino profilaxis",
            "Fluconazol profilaxis",
            "G-CSF",
            "Eritropoyetina",
            "Morfina rescate",
            "Gabapentina",
            "AAS",
            "DOAC",
            "IECA/ARA-II",
            "Insulina",
        ]
        med["medicaciones"] = _render_checklist_onoff(
            "Medicacion concomitante",
            med,
            "medicaciones",
            med_base,
            med_extra,
            "concom",
            columnas=3,
        )
        for item in med["medicaciones"]:
            st.markdown(f"<div class='im-mini-card'>{html.escape(item)}</div>", unsafe_allow_html=True)

    if paso == 7:
        st.markdown("#### Efectos adversos (AEs)")
        ae = estado["estado_aes"]
        ae_base = [
            "Neutropenia G1-2",
            "Neutropenia G3-4",
            "Anemia G1-2",
            "Trombocitopenia G1-2",
            "Neuropatia periferica G1-2",
            "Nauseas/vomitos G1-2",
            "Diarrea G1-2",
            "Infeccion respiratoria",
            "Mucositis oral",
            "Fatiga intensa",
        ]
        ae_extra = [
            "Fiebre neutropenica",
            "Trombosis venosa",
            "Rash cutaneo",
            "Toxicidad hepatica",
            "Toxicidad renal",
            "Reaccion infusion",
            "Hipocalcemia",
            "Hiperglucemia por corticoides",
        ]
        ae["eventos"] = _render_checklist_onoff(
            "AEs detectados",
            ae,
            "eventos",
            ae_base,
            ae_extra,
            "aes",
            columnas=3,
        )
        if ae["eventos"]:
            for item in ae["eventos"]:
                st.markdown(f"<div class='im-mini-card im-danger'>{html.escape(item)}</div>", unsafe_allow_html=True)
            st.error(f"AEs registrados: {len(ae['eventos'])}")
        else:
            st.success("Sin AEs registrados")

    if paso == 8:
        st.markdown("#### Decision de tratamiento")
        dec = estado["estado_decision"]
        opciones_dec = ["Pendiente", "Si administrar", "No administrar"]
        dec_actual = str(dec.get("decision", "Pendiente") or "Pendiente")
        if dec_actual not in opciones_dec:
            dec_actual = "Pendiente"
        dec["decision"] = st.radio(
            "Decision",
            options=opciones_dec,
            index=opciones_dec.index(dec_actual),
            horizontal=True,
            key=f"im_decision_{visita_id}",
        )
        dec["accion"] = st.text_input("Accion recomendada", value=str(dec.get("accion", "")), key=f"im_accion_{visita_id}")
        dec["motivo"] = st.text_area("Motivo", value=str(dec.get("motivo", "")), height=55, key=f"im_motivo_{visita_id}")

    if paso == 9:
        st.markdown("#### Confirmacion")
        dec = estado["estado_decision"]
        st.markdown(f"<div class='im-mini-card im-ok'>Decision: {html.escape(str(dec.get('decision', 'Pendiente')))}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='im-mini-card'>Accion: {html.escape(str(dec.get('accion', '') or '-'))}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='im-mini-card'>Motivo: {html.escape(str(dec.get('motivo', '') or '-'))}</div>", unsafe_allow_html=True)
        confirmado_key = f"im_confirmado_{visita_id}"
        if confirmado_key not in st.session_state:
            st.session_state[confirmado_key] = False
        if st.button("Confirmar decision", key=f"im_btn_confirmar_{visita_id}"):
            st.session_state[confirmado_key] = True
        if st.session_state[confirmado_key]:
            st.info("Decision confirmada y lista para notificar al equipo.")

    if paso == 10:
        st.markdown("#### Historia clinica generada")
        c = estado.get("estado_constantes", {})
        com = estado.get("estado_comentarios", {})
        pr = estado.get("estado_pruebas", {})
        far = estado.get("estado_farmacos_estudio", {})
        med = estado.get("estado_medicacion_concomitante", {})
        ae = estado.get("estado_aes", {})
        dec = estado.get("estado_decision", {})
        texto_auto = (
            f"Ensayo {visita_row.get('ensayo', '')}. Ciclo/Dia {visita_row.get('ciclo', '')}. Fecha {formatear_fecha_visita(visita_row.get('fecha'))}.\n"
            f"Constantes: TA {c.get('tension_arterial', '-')}, FC {c.get('fc', '-')}, FR {c.get('fr', '-')}, Temp {c.get('temperatura', '-')}, SatO2 {c.get('sat_o2', '-')}.\n"
            f"Antropometria: Peso {c.get('peso', '-')}, Talla {c.get('talla', '-')}, IMC {c.get('imc', '-')}, SC {c.get('superficie_corporal', '-')}.\n"
            f"Sintomas: {', '.join(com.get('sintomas', [])) if com.get('sintomas') else 'No referidos'}.\n"
            f"Comentario: {com.get('comentario_libre', '') or 'Sin comentarios'}.\n"
            f"Pruebas: {', '.join(pr.get('pruebas', [])) if pr.get('pruebas') else 'Sin pruebas'}.\n"
            f"Farmacos estudio: {', '.join(far.get('farmacos', [])) if far.get('farmacos') else 'No registrados'}.\n"
            f"Medicacion concomitante: {', '.join(med.get('medicaciones', [])) if med.get('medicaciones') else 'No registrada'}.\n"
            f"AEs: {', '.join(ae.get('eventos', [])) if ae.get('eventos') else 'Sin AEs'}.\n"
            f"Decision: {dec.get('decision', 'Pendiente')}. Accion: {dec.get('accion', '-')}. Motivo: {dec.get('motivo', '-')}."
        )
        if not str(estado.get("nota_clinica", "") or "").strip():
            estado["nota_clinica"] = texto_auto
        estado["nota_clinica"] = st.text_area(
            "Nota clinica editable",
            value=str(estado.get("nota_clinica", "")),
            height=72,
            key=f"im_nota_clinica_{visita_id}",
        )
        st.download_button(
            "Descargar nota clinica (.txt)",
            data=str(estado.get("nota_clinica", "")).encode("utf-8"),
            file_name=f"nota_clinica_visita_{visita_id}.txt",
            mime="text/plain",
            key=f"im_descarga_nota_{visita_id}",
        )

    if paso == 11:
        st.write("Protocolos, citas y notas en el menu lateral.")

    # Swipe usando window.parent.document para acceder a la página real (no el iframe)
    swipe_html = """
    <script>
    (function() {
        var doc = window.parent ? window.parent.document : document;
        var MIN_SWIPE = 52;
        var startX = 0, startY = 0, dragging = false;

        // Overlay visual de arrastre inyectado en la página real
        if (!doc.getElementById('swipe-overlay-im')) {
            var ov = doc.createElement('div');
            ov.id = 'swipe-overlay-im';
            ov.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:9998;transition:background 0.12s;';
            doc.body.appendChild(ov);
        }
        var overlay = doc.getElementById('swipe-overlay-im');

        function clickBoton(texto) {
            var btns = doc.querySelectorAll('button');
            for (var i = 0; i < btns.length; i++) {
                if (!btns[i].disabled && btns[i].innerText.trim() === texto) {
                    btns[i].click();
                    return;
                }
            }
        }

        function mostrarFeedback(dx) {
            var op = Math.min(Math.abs(dx) / 160, 0.38);
            if (dx > 0) {
                overlay.style.background = 'linear-gradient(to right, rgba(15,74,166,' + op + ') 0%, transparent 45%)';
            } else {
                overlay.style.background = 'linear-gradient(to left, rgba(15,74,166,' + op + ') 0%, transparent 45%)';
            }
        }

        function limpiarFeedback() {
            overlay.style.background = 'transparent';
        }

        // Touch (móvil)
        doc.addEventListener('touchstart', function(e) {
            startX = e.touches[0].clientX;
            startY = e.touches[0].clientY;
        }, {passive: true});

        doc.addEventListener('touchmove', function(e) {
            var dx = e.touches[0].clientX - startX;
            var dy = e.touches[0].clientY - startY;
            if (Math.abs(dx) > Math.abs(dy)) mostrarFeedback(dx);
        }, {passive: true});

        doc.addEventListener('touchend', function(e) {
            limpiarFeedback();
            var dx = e.changedTouches[0].clientX - startX;
            var dy = e.changedTouches[0].clientY - startY;
            if (Math.abs(dx) > Math.abs(dy) && Math.abs(dx) > MIN_SWIPE) {
                if (dx > 0) clickBoton('Atras');
                else clickBoton('Siguiente');
            }
        }, {passive: true});

        // Mouse (desktop)
        doc.addEventListener('mousedown', function(e) {
            dragging = true;
            startX = e.clientX;
        });
        doc.addEventListener('mousemove', function(e) {
            if (dragging) mostrarFeedback(e.clientX - startX);
        });
        doc.addEventListener('mouseup', function(e) {
            if (!dragging) return;
            dragging = false;
            limpiarFeedback();
            var dx = e.clientX - startX;
            if (Math.abs(dx) > MIN_SWIPE) {
                if (dx > 0) clickBoton('Atras');
                else clickBoton('Siguiente');
            }
        });
    })();
    </script>
    """
    components.html(swipe_html, height=0)

    # Botones ocultos visualmente pero necesarios para que Streamlit capture el clic
    nav1, nav2, nav3 = st.columns([1, 1.2, 1])
    if nav1.button("Atras", disabled=(paso <= 1), key=f"im_prev_{visita_id}"):
        st.session_state[step_key] = max(1, paso - 1)
        st.rerun()

    if nav2.button("Guardar", type="primary", key=f"im_guardar_{visita_id}"):
        guardar_estado_interfaz_medica(visita_id, estado)
        st.success("Interfaz medica guardada.")

    if nav3.button("Siguiente", disabled=(paso >= len(pasos)), key=f"im_next_{visita_id}"):
        guardar_estado_interfaz_medica(visita_id, estado)
        st.session_state[step_key] = min(len(pasos), paso + 1)
        st.rerun()


requerir_login_si_configurado()

# Inicializamos DB una vez por sesion para evitar coste en cada rerun.
if not st.session_state.get("_db_inicializada", False):
    init_db()
    st.session_state["_db_inicializada"] = True

# Backup diario automatico a la carpeta local de red.
_hoy_str = datetime.now().strftime("%Y%m%d")
_backup_ruta_actual = resolver_carpeta_backup_diario()
_backup_hoy_existe = existe_backup_diario_hoy(_backup_ruta_actual)
if st.session_state.get("_backup_diario_fecha") != _hoy_str or not _backup_hoy_existe:
    _backup_ok, _backup_ruta = backup_diario_ensayos()
    if _backup_ok:
        st.session_state["_backup_diario_fecha"] = _hoy_str
        st.session_state["_backup_diario_ruta"] = _backup_ruta
elif _backup_ruta_actual:
    st.session_state["_backup_diario_ruta"] = _backup_ruta_actual

# --- INTERFAZ PRINCIPAL ---
if LOGO_PATH:
    renderizar_logo_sidebar(LOGO_PATH)
else:
    st.sidebar.caption("Logo no encontrado")

if _auth_configurada() and st.sidebar.button("Cerrar sesión", key="btn_logout_app"):
    st.session_state["_auth_ok"] = False
    st.rerun()

_ruta_backup_mostrada = st.session_state.get("_backup_diario_ruta", "")

secciones_principales = [
    "Copia de seguridad",
    "Agenda",
    "Registro de kits",
    "Citas ojos",
    "Calendario DREAMM10",
    "Prot. ensayo",
    "Ficha paciente",
    "Interfaz medica",
    "Check list",
    "Notas enfermeria",
    "Notas coordinacion",
    "Adendas",
    "Esquemas",
]
seccion_activa = st.sidebar.radio("Navegación", options=secciones_principales, key="seccion_principal")

ensayos_con_adendas = get_ensayos_con_adendas_pendientes()
if ensayos_con_adendas:
    st.sidebar.markdown("#### 📌 Adendas pendientes")
    pendientes_paciente = [
        item for item in ensayos_con_adendas
        if str(item.get("paciente", "")).strip()
    ]
    st.sidebar.caption(
        f"{len(pendientes_paciente)} paciente(s) con adenda pendiente"
    )
    for item in ensayos_con_adendas:
        etiqueta = str(item.get("etiqueta", "")).strip()
        if etiqueta:
            st.sidebar.markdown(f"• {etiqueta}")

if seccion_activa == "Copia de seguridad":
    st.subheader("🗂️ Copias de seguridad")
    if _ruta_backup_mostrada:
        st.info(f"Ruta activa de backup: {_ruta_backup_mostrada}")
    else:
        st.warning("No hay ruta de backup accesible. Revisa BACKUP_ENSAYOS_DIR.")

    if st.button("Forzar backup ahora", key="btn_forzar_backup_tab"):
        _ok_forzado, _ruta_forzada = backup_diario_ensayos(forzar=True)
        if _ok_forzado:
            st.session_state["_backup_diario_ruta"] = _ruta_forzada
            _ruta_backup_mostrada = _ruta_forzada
            st.success(f"Backup generado en: {_ruta_forzada}")
        else:
            st.error("No se pudo generar el backup ahora. Revisa la ruta de destino.")

    if st.button("Preparar descarga backup", key="btn_preparar_backup_pc_tab"):
        _bytes_backup, _nombre_backup, _mime_backup = construir_backup_descargable()
        if _bytes_backup:
            st.session_state["_backup_descarga_bytes"] = _bytes_backup
            st.session_state["_backup_descarga_nombre"] = _nombre_backup
            st.session_state["_backup_descarga_mime"] = _mime_backup
            st.success("Backup listo para descargar")
        else:
            st.error("No se pudo preparar el backup para descarga")

    if st.session_state.get("_backup_descarga_bytes"):
        st.download_button(
            "Descargar backup al PC",
            data=st.session_state["_backup_descarga_bytes"],
            file_name=st.session_state.get("_backup_descarga_nombre", "backup.db"),
            mime=st.session_state.get("_backup_descarga_mime", "application/octet-stream"),
            key="btn_descargar_backup_pc_tab",
        )

if seccion_activa == "Registro de kits":
    renderizar_registro_kits_integrado()

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

            if (codigo_sel or nombre_sel) and ensayo_sel:
                adenda_paciente = get_adenda_paciente(codigo_sel, nombre_sel, ensayo_sel)
                with st.form("form_adenda_paciente_ficha"):
                    texto_adenda_paciente = st.text_area(
                        "Adenda asociada al paciente",
                        value=adenda_paciente.get("texto", ""),
                        height=140,
                        key=f"ficha_adenda_paciente_{normalizar_clave_paciente(codigo_sel)}_{normalizar_clave_paciente(ensayo_sel)}"
                    )
                    guardar_adenda_pac = st.form_submit_button("Guardar adenda paciente", type="primary")
                    if guardar_adenda_pac:
                        guardar_adenda_paciente(codigo_sel, nombre_sel, ensayo_sel, texto_adenda_paciente.strip())
                        st.success("Adenda del paciente guardada.")
                        st.rerun()
                fecha_mod_pac = adenda_paciente.get("fecha_modificacion", "")
                if fecha_mod_pac:
                    st.caption(f"Ultima modificación adenda paciente: {fecha_mod_pac}")
                st.divider()

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
                    df_ficha = df_ficha.rename(
                        columns={
                            "fecha_evaluacion": "fecha_revision",
                            "resultado": "resultado_ocular",
                            "sede": "sede_ocular",
                            "agenda_hospitalaria": "agenda_hospitalaria_ocular",
                        }
                    )
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
                    df_ficha = df_ficha.rename(
                        columns={
                            "fecha_evaluacion": "fecha_revision",
                            "resultado": "resultado_ocular",
                            "sede": "sede_ocular",
                            "agenda_hospitalaria": "agenda_hospitalaria_ocular",
                        }
                    )
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
                        "sede_ocular": "REVISION OCULAR (SEDE)",
                        "agenda_hospitalaria_ocular": "AGENDA HOSPITALARIA (OCULAR)",
                        "fecha_revision": "REVISION OCULAR (FECHA)",
                        "resultado_ocular": "RESULTADO OCULAR"
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
                        "REVISION OCULAR (SEDE)",
                        "AGENDA HOSPITALARIA (OCULAR)",
                        "REVISION OCULAR (FECHA)",
                        "RESULTADO OCULAR"
                    ]
                ]

                def colorear_filas(row):
                    color = colores.get(row.name, "")
                    if not color:
                        return [""] * len(row)
                    return [f"background-color: {color}"] * len(row)

                st.caption("Verde: visitas realizadas. Amarillo: hoy. Rojo: pendientes.")
                st.dataframe(df_ficha.style.apply(colorear_filas, axis=1), use_container_width=True)

if seccion_activa == "Interfaz medica":
    render_interfaz_medica()

if seccion_activa == "Citas ojos":
    st.subheader("👁️ Citas de ojos")

    df_visitas = get_visitas()
    if df_visitas.empty:
        st.info("No hay visitas registradas.")
    else:
        with st.expander("➕ Añadir paciente fuera de ensayo", expanded=False):
            with st.form("form_nuevo_fuera_ensayo"):
                col_nuevo_1, col_nuevo_2 = st.columns(2)
                codigo_nuevo = col_nuevo_1.text_input("Código", key="ojos_fuera_codigo")
                nombre_nuevo = col_nuevo_2.text_input("Nombre", key="ojos_fuera_nombre")
                fecha_visita_nueva = st.date_input("Fecha de visita", value=fecha_hoy_local(), key="ojos_fuera_fecha")
                crear_fuera = st.form_submit_button("Crear paciente Fuera de Ensayo", type="primary")
                if crear_fuera:
                    if not str(codigo_nuevo or "").strip() and not str(nombre_nuevo or "").strip():
                        st.warning("Introduce al menos código o nombre.")
                    else:
                        data_nueva = {
                            "nombre": str(nombre_nuevo or "").strip(),
                            "codigo": str(codigo_nuevo or "").strip(),
                            "ensayo": "Fuera de Ensayo",
                            "ciclo": "",
                            "kits": "",
                            "tablet": False,
                            "medula": False,
                            "otras_pruebas": "",
                            "comentarios": "",
                        }
                        guardar_visita(fecha_visita_nueva.isoformat(), data_nueva)
                        st.success("Paciente creado en Fuera de Ensayo.")
                        st.rerun()

        with st.expander("🛟 Recuperar paciente desde backups", expanded=False):
            st.caption("Restaura un paciente y sus visitas en la base actual usando los backups locales de la app.")
            with st.form("form_recuperar_paciente_backup"):
                codigo_recuperar = st.text_input("Código a recuperar", value="000601")
                recuperar = st.form_submit_button("Recuperar paciente", type="primary")
                if recuperar:
                    resultado = restaurar_paciente_desde_backups_locales(codigo_recuperar)
                    if resultado.get("ok"):
                        st.success(
                            f"{resultado.get('mensaje')} Visitas en backups: {resultado.get('visitas_backup', 0)}. "
                            f"Insertadas: {resultado.get('visitas_insertadas', 0)}. "
                            f"Totales ahora: {resultado.get('visitas_totales', 0)}."
                        )
                        st.rerun()
                    else:
                        st.warning(resultado.get("mensaje", "No se pudo recuperar el paciente."))

        df_visitas = df_visitas.copy()
        df_visitas["ensayo"] = df_visitas["ensayo"].apply(_normalizar_ensayo_ojos)
        df_visitas = df_visitas[df_visitas["ensayo"].isin(ENSAYOS_OJOS_PERMITIDOS)].copy()
        if df_visitas.empty:
            st.info("No hay pacientes de DREAMM 10, DREAMM-8 o Fuera de Ensayo.")
            st.caption("Puedes crear un paciente en 'Fuera de Ensayo' con el formulario superior.")
            st.stop()

        with st.expander("🧹 Limpiar filas sin paciente", expanded=False):
            st.caption("Elimina filas de Citas ojos que no tienen ni código ni nombre.")
            if st.button("Eliminar filas vacías", key="ojos_btn_limpiar_vacios"):
                borradas_vacias = borrar_visitas_sin_paciente_citas_ojos()
                if borradas_vacias:
                    st.success(f"Filas vacías eliminadas: {borradas_vacias}")
                    st.rerun()
                else:
                    st.info("No se encontraron filas vacías para eliminar.")

        # Dejamos una sola fila por paciente en Citas ojos (la visita mas reciente),
        # deduplicando por codigo/nombre sin depender del ensayo.
        df_visitas["_fecha_dt"] = pd.to_datetime(df_visitas["fecha"], errors="coerce")

        def _clave_paciente_ojos(row):
            codigo_norm = normalizar_clave_paciente(row.get("codigo"))
            if codigo_norm:
                return f"codigo|{codigo_norm}"
            nombre_norm = normalizar_clave_paciente(row.get("nombre"))
            if nombre_norm:
                return f"nombre|{nombre_norm}"
            return ""

        df_visitas["_clave_paciente"] = df_visitas.apply(_clave_paciente_ojos, axis=1)
        df_visitas = df_visitas.sort_values(by=["_fecha_dt", "id"], ascending=[False, False])
        con_clave = df_visitas[df_visitas["_clave_paciente"].astype(str).str.strip() != ""]
        con_clave = con_clave.drop_duplicates(subset=["_clave_paciente"], keep="first")
        df_visitas = con_clave.copy()

        if df_visitas.empty:
            st.info("No hay pacientes válidos en Citas de ojos (con código o nombre).")
            st.stop()

        with st.expander("🗑️ Eliminar paciente de Citas de ojos", expanded=False):
            opciones_borrado = []
            mapa_borrado = {}
            df_borrado = df_visitas.sort_values(by=["ensayo", "codigo", "nombre"], na_position="last")
            for _, row in df_borrado.iterrows():
                codigo_b = "" if pd.isna(row.get("codigo")) else str(row.get("codigo"))
                nombre_b = "" if pd.isna(row.get("nombre")) else str(row.get("nombre"))
                ensayo_b = "" if pd.isna(row.get("ensayo")) else str(row.get("ensayo"))
                etiqueta_b = f"{codigo_b} | {nombre_b} | {ensayo_b}".strip(" |")
                if etiqueta_b in mapa_borrado:
                    continue
                opciones_borrado.append(etiqueta_b)
                mapa_borrado[etiqueta_b] = {
                    "codigo": codigo_b,
                    "nombre": nombre_b,
                }

            if not opciones_borrado:
                st.caption("No hay pacientes para eliminar.")
            else:
                sel_borrar = st.selectbox(
                    "Paciente a eliminar",
                    options=opciones_borrado,
                    key="ojos_paciente_borrar",
                )
                confirmar_borrado = st.checkbox(
                    "Confirmo eliminación del paciente en Citas de ojos",
                    key="ojos_confirmar_borrado",
                )
                if st.button("Eliminar paciente", type="primary", key="ojos_btn_borrar_paciente"):
                    if not confirmar_borrado:
                        st.warning("Marca la confirmación antes de eliminar.")
                    else:
                        datos_b = mapa_borrado.get(sel_borrar, {})
                        borradas = borrar_paciente_citas_ojos(datos_b.get("codigo", ""), datos_b.get("nombre", ""))
                        if borradas > 0:
                            st.success(f"Visitas eliminadas: {borradas}")
                            st.rerun()
                        else:
                            st.info("No se encontraron visitas para eliminar.")

        df_rev = get_revisiones_oculares_df()
        base = df_visitas.copy()
        base = base.merge(df_rev, how="left", left_on="id", right_on="visita_id")

        tabla = pd.DataFrame()
        tabla["VISITA_ID"] = base["id"].astype(int)
        tabla["CODIGO"] = base["codigo"].fillna("").astype(str)
        tabla["NOMBRE"] = base["nombre"].fillna("").astype(str)
        tabla["ENSAYO"] = base["ensayo"].apply(_normalizar_ensayo_ojos)
        tabla["SEDE"] = base["sede"].fillna("").astype(str)
        tabla["MEDICO"] = base["medico"].fillna("").astype(str)
        tabla["AGENDA HOSPITALARIA"] = base["agenda_hospitalaria"].fillna("").astype(str)
        tabla["FECHA EVALUACION"] = pd.to_datetime(base["fecha_evaluacion"], errors="coerce").dt.date
        tabla["FECHAS PREVIAS"] = base["fechas_previas"].fillna("").astype(str)
        tabla["RESULTADO"] = base["resultado"].fillna("").astype(str)
        tabla["REALIZADO"] = False

        tabla = tabla.sort_values(by=["ENSAYO", "CODIGO", "NOMBRE"], na_position="last").reset_index(drop=True)

        def _estado_fila(row):
            if str(row.get("MEDICO") or "").strip():
                return "CITADO"
            if pd.notna(row.get("FECHA EVALUACION")):
                return "PENDIENTE DE CITA"
            return ""

        tabla["ESTADO"] = tabla.apply(_estado_fila, axis=1)
        tabla = tabla.set_index("VISITA_ID")

        st.caption("Edición directa en la tabla. Marca 'REALIZADO' y guarda para pasar la fecha actual a 'FECHAS PREVIAS'.")
        editada = st.data_editor(
            tabla,
            key="citas_ojos_editor",
            hide_index=True,
            use_container_width=True,
            disabled=["CODIGO", "NOMBRE", "FECHAS PREVIAS", "ESTADO"],
            column_config={
                "ENSAYO": st.column_config.SelectboxColumn(
                    "ENSAYO",
                    options=ENSAYOS_OJOS_PERMITIDOS,
                    required=True,
                ),
                "SEDE": st.column_config.SelectboxColumn(
                    "SEDE",
                    options=["", "cabueñes", "puerta de la villa", "pumarin"],
                ),
                "MEDICO": st.column_config.SelectboxColumn(
                    "MEDICO",
                    options=[""] + MEDICOS_OJOS_PERMITIDOS,
                    width="medium",
                ),
                "AGENDA HOSPITALARIA": st.column_config.TextColumn("AGENDA HOSPITALARIA"),
                "FECHA EVALUACION": st.column_config.DateColumn("FECHA EVALUACION", format="DD/MM/YYYY"),
                "RESULTADO": st.column_config.TextColumn("RESULTADO"),
                "REALIZADO": st.column_config.CheckboxColumn("REALIZADO"),
                "ESTADO": st.column_config.TextColumn("ESTADO", width="large"),
            },
        )

        if st.button("Guardar cambios de la tabla", type="primary", key="guardar_tabla_citas_ojos"):
            cambios = 0
            original = tabla
            nuevo = editada

            for visita_id, fila_nueva in nuevo.iterrows():
                fila_orig = original.loc[visita_id]

                ensayo_nuevo = _normalizar_ensayo_ojos(fila_nueva.get("ENSAYO"))
                ensayo_orig = _normalizar_ensayo_ojos(fila_orig.get("ENSAYO"))
                if ensayo_nuevo != ensayo_orig:
                    actualizar_ensayo_visita(int(visita_id), ensayo_nuevo)
                    cambios += 1

                sede_nueva = str(fila_nueva.get("SEDE") or "").strip().lower()
                medico_nueva = str(fila_nueva.get("MEDICO") or "").strip().upper()
                if medico_nueva and medico_nueva not in MEDICOS_OJOS_PERMITIDOS:
                    medico_nueva = "OTRO"
                agenda_nueva = str(fila_nueva.get("AGENDA HOSPITALARIA") or "").strip()
                resultado_nueva = str(fila_nueva.get("RESULTADO") or "").strip()
                fecha_nueva_val = fila_nueva.get("FECHA EVALUACION")
                fecha_nueva = "" if pd.isna(fecha_nueva_val) else str(fecha_nueva_val)
                realizado_nuevo = bool(fila_nueva.get("REALIZADO"))

                sede_orig = str(fila_orig.get("SEDE") or "").strip().lower()
                medico_orig = str(fila_orig.get("MEDICO") or "").strip().upper()
                agenda_orig = str(fila_orig.get("AGENDA HOSPITALARIA") or "").strip()
                resultado_orig = str(fila_orig.get("RESULTADO") or "").strip()
                fecha_orig_val = fila_orig.get("FECHA EVALUACION")
                fecha_orig = "" if pd.isna(fecha_orig_val) else str(fecha_orig_val)

                # Si se marca como realizado, movemos la fecha actual a historial y limpiamos fecha activa.
                fecha_guardar = "" if realizado_nuevo else fecha_nueva

                if (
                    sede_nueva != sede_orig
                    or medico_nueva != medico_orig
                    or agenda_nueva != agenda_orig
                    or resultado_nueva != resultado_orig
                    or fecha_guardar != fecha_orig
                ):
                    guardar_revision_ocular(
                        int(visita_id),
                        sede_nueva,
                        medico_nueva,
                        agenda_nueva,
                        fecha_guardar,
                        resultado_nueva,
                    )
                    cambios += 1

            if cambios:
                st.success(f"Cambios guardados: {cambios}")
                st.rerun()
            else:
                st.info("No hay cambios para guardar.")

if seccion_activa == "Calendario DREAMM10":
    st.subheader("🗓️ Calendario ciclos DREAMM10")
    os.makedirs(DREAMM10_XLSX_DIR, exist_ok=True)
    st.caption(f"Carpeta de trabajo: {DREAMM10_XLSX_DIR}")

    if "dreamm10_archivos_memoria" not in st.session_state:
        st.session_state["dreamm10_archivos_memoria"] = {}

    archivos_subidos = st.file_uploader(
        "Adjuntar tablas Excel (.xlsx)",
        type=["xlsx"],
        accept_multiple_files=True,
        key="dreamm10_xlsx_uploader",
    )

    if archivos_subidos:
        cargados = 0
        guardados = 0
        guardados_db = 0
        for archivo in archivos_subidos:
            nombre_seguro = os.path.basename(archivo.name)
            contenido = archivo.getvalue()
            st.session_state["dreamm10_archivos_memoria"][nombre_seguro] = contenido
            cargados += 1

            if guardar_excel_dreamm10_en_db(nombre_seguro, contenido):
                guardados_db += 1

            destino = os.path.join(DREAMM10_XLSX_DIR, nombre_seguro)
            try:
                with open(destino, "wb") as salida:
                    salida.write(contenido)
                guardados += 1
            except Exception:
                # En Streamlit Cloud puede fallar escritura en disco; mantenemos uso en memoria.
                pass

        st.cache_data.clear()
        if guardados:
            st.success(
                f"Excel cargado en memoria ({cargados}), guardado en BD ({guardados_db}) y en carpeta ({guardados})."
            )
        else:
            st.success(f"Excel cargado en memoria ({cargados}) y guardado en BD ({guardados_db}).")

    archivos_memoria = dict(st.session_state.get("dreamm10_archivos_memoria", {}))
    archivos_db = obtener_excels_dreamm10_db()
    excels = listar_excels(DREAMM10_XLSX_DIR)
    fuentes = []
    for nombre in sorted(archivos_memoria.keys()):
        fuentes.append((f"🟢 Subido ahora | {nombre}", "memoria", nombre))
    for nombre in sorted(archivos_db.keys()):
        fuentes.append((f"🗄️ Permanente (BD) | {nombre}", "db", nombre))
    for nombre in excels:
        fuentes.append((f"📁 Carpeta | {nombre}", "carpeta", nombre))

    if not fuentes:
        st.info("No hay archivos .xlsx en la carpeta DREAMM10. Sube al menos uno para generar el calendario.")
    else:
        mapa_fuentes = {etiqueta: (origen, nombre) for etiqueta, origen, nombre in fuentes}
        etiqueta_sel = st.selectbox(
            "Archivo Excel",
            options=list(mapa_fuentes.keys()),
            key="dreamm10_excel_sel",
        )
        origen_sel, archivo_sel = mapa_fuentes[etiqueta_sel]

        bytes_excel = b""
        if origen_sel == "memoria":
            bytes_excel = archivos_memoria.get(archivo_sel, b"")
        elif origen_sel == "db":
            bytes_excel = archivos_db.get(archivo_sel, b"")
        else:
            ruta_excel_sel = os.path.join(DREAMM10_XLSX_DIR, archivo_sel)
            try:
                with open(ruta_excel_sel, "rb") as f_excel:
                    bytes_excel = f_excel.read()
            except Exception as e:
                st.error(f"No se pudo abrir el Excel de carpeta: {e}")

        if bytes_excel:
            st.download_button(
                "Descargar Excel seleccionado",
                data=bytes_excel,
                file_name=archivo_sel,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="dreamm10_descargar_excel",
            )

        try:
            if not bytes_excel:
                hojas_excel = {}
            else:
                hojas_excel = cargar_excel_desde_bytes(bytes_excel)
        except Exception as e:
            st.error(f"No se pudo leer el Excel seleccionado: {e}")
            hojas_excel = {}

        if not hojas_excel:
            st.warning("El archivo no contiene hojas con datos legibles.")
        else:
            nombres_hojas = list(hojas_excel.keys())
            hojas_mostrar = nombres_hojas
            st.caption(f"Procesando automáticamente todas las pestañas del Excel como pacientes: {len(hojas_mostrar)}")

            eventos_dreamm10 = []
            registros_dreamm10 = []
            tabla_registros = pd.DataFrame()
            for hoja in hojas_mostrar:
                df_hoja = hojas_excel.get(hoja, pd.DataFrame())
                if df_hoja.empty:
                    continue
                registros_dreamm10.extend(extraer_registros_visitas_dreamm10(df_hoja, nombre_hoja=hoja))

            st.session_state["dreamm10_registros_map"] = {
                str(i): r for i, r in enumerate(registros_dreamm10)
            }

            eventos_dreamm10 = construir_eventos_desde_registros_dreamm10(registros_dreamm10)

            if registros_dreamm10:
                tabla_registros = pd.DataFrame(registros_dreamm10)
                columnas_tabla = [
                    "fecha",
                    "codigo",
                    "nombre",
                    "ensayo",
                    "ciclo",
                    "w",
                    "c",
                    "dosis_lena",
                    "ventana_mas",
                    "ventana_menos",
                    "comentarios",
                    "origen_hoja",
                ]
                for col in columnas_tabla:
                    if col not in tabla_registros.columns:
                        tabla_registros[col] = ""
                tabla_registros = tabla_registros[columnas_tabla].sort_values(by=["fecha", "codigo", "nombre"]).reset_index(drop=True)
                tabla_registros["fecha"] = tabla_registros["fecha"].apply(_formatear_fecha_es_sin_hora)

                _, duplicados = insertar_registros_dreamm10_en_tabla(registros_dreamm10)
                st.caption(
                    "DREAMM10 aislado: estos registros no se guardan en Agenda/Ficha paciente. "
                    f"Duplicados detectados en el propio Excel: {duplicados}."
                )
            else:
                st.info("No se detectaron registros de fechas para trasladar a la tabla.")

            if not eventos_dreamm10:
                st.warning("No se detectaron fechas válidas en columna C para construir el calendario.")
                with st.expander("Diagnóstico de fechas detectadas", expanded=True):
                    for hoja in hojas_mostrar:
                        df_diag = hojas_excel.get(hoja, pd.DataFrame())
                        if df_diag.empty:
                            continue
                        st.markdown(f"**{hoja}**")
                        diag = diagnostico_columnas_fecha(df_diag)
                        if diag.empty:
                            st.caption("Sin columnas con valores convertibles a fecha.")
                        else:
                            st.dataframe(diag, use_container_width=True, height=180)
            else:
                st.success(f"Eventos totales en calendario: {len(eventos_dreamm10)}")
                opciones_cal_dreamm10 = {
                    "editable": False,
                    "navLinks": True,
                    "initialView": "dayGridMonth",
                    "headerToolbar": {
                        "left": "today prev,next",
                        "center": "title",
                        "right": "dayGridMonth,listWeek",
                    },
                    "initialDate": fecha_hoy_local().isoformat(),
                    "firstDay": 1,
                    "selectable": True,
                }
                estado_cal_dreamm10 = calendar(
                    events=eventos_dreamm10,
                    options=opciones_cal_dreamm10,
                    key="calendar_dreamm10",
                )

                if "dreamm10_fecha_detalle" not in st.session_state:
                    st.session_state["dreamm10_fecha_detalle"] = fecha_hoy_local()
                if "dreamm10_evento_sel" not in st.session_state:
                    st.session_state["dreamm10_evento_sel"] = {}

                if estado_cal_dreamm10 and estado_cal_dreamm10.get("dateClick"):
                    fecha_click = estado_cal_dreamm10["dateClick"].get("date", "")
                    if fecha_click:
                        st.session_state["dreamm10_fecha_detalle"] = pd.to_datetime(fecha_click, errors="coerce").date()

                if estado_cal_dreamm10 and estado_cal_dreamm10.get("eventClick"):
                    evento_click = estado_cal_dreamm10["eventClick"].get("event", {})
                    props_click = evento_click.get("extendedProps", {})

                    registro_idx = props_click.get("registro_idx")
                    if registro_idx is None:
                        ev_id = str(evento_click.get("id") or "").strip()
                        if ev_id:
                            try:
                                registro_idx = int(ev_id)
                            except Exception:
                                registro_idx = None

                    registro_sel = {}
                    if registro_idx is not None:
                        registro_sel = st.session_state.get("dreamm10_registros_map", {}).get(str(registro_idx), {})

                    if not registro_sel:
                        fecha_evento_fallback = (
                            evento_click.get("start")
                            or evento_click.get("startStr")
                            or ""
                        )
                        titulo_fallback = str(evento_click.get("title") or "")
                        for reg in registros_dreamm10:
                            if str(reg.get("fecha") or "") != str(fecha_evento_fallback)[:10]:
                                continue
                            if str(reg.get("codigo") or "") and str(reg.get("codigo") or "") in titulo_fallback:
                                registro_sel = reg
                                break

                    st.session_state["dreamm10_evento_sel"] = {
                        "paciente": str(registro_sel.get("nombre") or props_click.get("paciente") or ""),
                        "codigo": str(registro_sel.get("codigo") or props_click.get("codigo") or ""),
                        "fecha": str(registro_sel.get("fecha") or props_click.get("fecha") or ""),
                        "week": str(registro_sel.get("w") or props_click.get("week") or ""),
                        "ciclo": str(registro_sel.get("c") or props_click.get("ciclo") or ""),
                        "dosis_lena": str(registro_sel.get("dosis_lena") or props_click.get("dosis_lena") or ""),
                        "ventana_mas": str(registro_sel.get("ventana_mas") or props_click.get("ventana_mas") or ""),
                        "ventana_menos": str(registro_sel.get("ventana_menos") or props_click.get("ventana_menos") or ""),
                        "contenido": str(registro_sel.get("comentarios") or props_click.get("contenido") or ""),
                        "origen_hoja": str(registro_sel.get("origen_hoja") or props_click.get("origen_hoja") or ""),
                    }

                    fecha_evento = (
                        evento_click.get("start")
                        or evento_click.get("startStr")
                        or ""
                    )
                    if fecha_evento:
                        st.session_state["dreamm10_fecha_detalle"] = pd.to_datetime(fecha_evento, errors="coerce").date()

                evento_sel = st.session_state.get("dreamm10_evento_sel", {})
                if evento_sel:
                    st.markdown("### 👤 Paciente seleccionado")
                    c1, c2 = st.columns(2)
                    c1.write(f"Paciente: {evento_sel.get('paciente', '')}")
                    c1.write(f"Código: {evento_sel.get('codigo', '')}")
                    c1.write(f"Fecha: {_formatear_fecha_es_sin_hora(evento_sel.get('fecha', ''))}")
                    c2.write(f"Week: {evento_sel.get('week', '')}")
                    c2.write(f"Ciclo: {evento_sel.get('ciclo', '')}")
                    c2.write(f"Dosis: {evento_sel.get('dosis_lena', '')}")
                    c2.write(f"Origen (pestaña): {evento_sel.get('origen_hoja', '')}")
                    st.write(f"Ventana +: {evento_sel.get('ventana_mas', '')}")
                    st.write(f"Ventana -: {evento_sel.get('ventana_menos', '')}")
                    st.write(f"Contenido: {evento_sel.get('contenido', '')}")

                if not tabla_registros.empty:
                    st.markdown("### 📌 Contenido del día")
                    fecha_detalle = st.date_input(
                        "Selecciona día",
                        value=st.session_state.get("dreamm10_fecha_detalle", fecha_hoy_local()),
                        key="dreamm10_fecha_detalle_input",
                    )
                    st.session_state["dreamm10_fecha_detalle"] = fecha_detalle

                    fecha_txt = fecha_detalle.strftime("%d/%m/%Y")
                    dia_df = tabla_registros[tabla_registros["fecha"].astype(str) == fecha_txt].copy()
                    if dia_df.empty:
                        st.info("No hay contenido para este día.")
                    else:
                        dia_df = dia_df[["nombre", "w", "c", "dosis_lena", "ventana_mas", "ventana_menos", "comentarios"]].reset_index(drop=True)
                        dia_df = dia_df.rename(
                            columns={
                                "nombre": "PACIENTE",
                                "w": "WEEK",
                                "c": "CICLO",
                                "dosis_lena": "DOSIS",
                                "ventana_mas": "VENTANA +",
                                "ventana_menos": "VENTANA -",
                                "comentarios": "CONTENIDO",
                            }
                        )
                        st.dataframe(dia_df, use_container_width=True, height=220)

            with st.expander("Vista previa de tablas", expanded=False):
                hoja_preview = st.selectbox(
                    "Hoja para previsualizar",
                    options=nombres_hojas,
                    key="dreamm10_preview_sheet",
                )
                df_preview = hojas_excel.get(hoja_preview, pd.DataFrame())
                st.dataframe(df_preview, use_container_width=True, height=340)

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

        with st.expander("Importar checklist desde Excel", expanded=False):
            bytes_excel_checklist = None
            origen_excel_checklist = ""

            if os.path.isfile(CHECKLIST_GLOBAL_XLSX):
                bytes_excel_checklist = leer_archivo_binario(CHECKLIST_GLOBAL_XLSX)
                origen_excel_checklist = f"Archivo versionado detectado: {os.path.basename(CHECKLIST_GLOBAL_XLSX)}"

            archivo_checklist_subido = st.file_uploader(
                "Sube otro Excel de checklist (.xlsx) si quieres reemplazar el archivo detectado",
                type=["xlsx"],
                key="checklist_excel_uploader"
            )
            if archivo_checklist_subido is not None:
                bytes_excel_checklist = archivo_checklist_subido.getvalue()
                origen_excel_checklist = f"Archivo subido: {archivo_checklist_subido.name}"

            if bytes_excel_checklist is None:
                st.info("No se ha encontrado el Excel de checklist en la carpeta raíz y tampoco se ha subido uno manualmente.")
            else:
                st.markdown("**Paso 1. Fuente del Excel**")
                st.caption(origen_excel_checklist)
                try:
                    protocolos_excel, items_por_protocolo = resumir_checklist_excel_desde_bytes(bytes_excel_checklist)
                except Exception as exc:
                    st.error(f"No se pudo procesar el Excel del checklist: {exc}")
                else:
                    if not protocolos_excel:
                        st.warning("El Excel no contiene protocolos importables en las hojas esperadas.")
                    else:
                        st.markdown("**Paso 2. Selección del protocolo**")
                        sugeridos = _buscar_protocolos_relacionados(ensayo_sel, protocolos_excel)
                        protocolo_por_defecto = sugeridos[0] if sugeridos else protocolos_excel[0]
                        indice_defecto = protocolos_excel.index(protocolo_por_defecto)

                        col_protocolo, col_sugerencia = st.columns([3, 2])
                        with col_protocolo:
                            protocolo_excel_sel = st.selectbox(
                                "Protocolo del Excel",
                                options=protocolos_excel,
                                index=indice_defecto,
                                key=f"checklist_excel_protocolo_{ensayo_sel}"
                            )
                        with col_sugerencia:
                            if sugeridos:
                                st.success(f"Sugerido para {ensayo_sel}: {protocolo_por_defecto}")
                            else:
                                st.info("No hay coincidencia automática fuerte; revisa el protocolo seleccionado.")

                        items_excel = items_por_protocolo.get(protocolo_excel_sel, [])

                        filas_preview = [
                            {
                                "Tipo": clasificar_item_checklist(item),
                                "Item": item
                            }
                            for item in items_excel
                        ]
                        df_preview = pd.DataFrame(filas_preview)

                        total_items = len(items_excel)
                        total_visitas = int((df_preview["Tipo"] == "Visitas").sum()) if not df_preview.empty else 0
                        total_analitos = int((df_preview["Tipo"] == "Analitos").sum()) if not df_preview.empty else 0

                        st.markdown("**Paso 3. Vista previa e importación**")
                        m1, m2, m3 = st.columns(3)
                        with m1:
                            st.metric("Total items", total_items)
                        with m2:
                            st.metric("Visitas", total_visitas)
                        with m3:
                            st.metric("Analitos", total_analitos)

                        if items_excel:
                            filtro_txt = st.text_input(
                                "Filtrar por texto",
                                value="",
                                key=f"checklist_excel_filtro_{ensayo_sel}",
                                placeholder="Ejemplo: screening, coagulación, C1D1..."
                            ).strip()

                            df_filtrado = df_preview.copy()
                            if filtro_txt:
                                patron = re.escape(filtro_txt)
                                df_filtrado = df_filtrado[
                                    df_filtrado["Item"].astype(str).str.contains(patron, case=False, na=False)
                                ]

                            tab_todos, tab_visitas, tab_analitos = st.tabs(["Todos", "Visitas", "Analitos"])
                            with tab_todos:
                                st.dataframe(df_filtrado.head(30), use_container_width=True, hide_index=True)
                            with tab_visitas:
                                st.dataframe(
                                    df_filtrado[df_filtrado["Tipo"] == "Visitas"].head(30),
                                    use_container_width=True,
                                    hide_index=True
                                )
                            with tab_analitos:
                                st.dataframe(
                                    df_filtrado[df_filtrado["Tipo"] == "Analitos"].head(30),
                                    use_container_width=True,
                                    hide_index=True
                                )

                            if st.button("Importar protocolo del Excel", key="checklist_importar_excel"):
                                items_nuevos = add_checklist_items_bulk(ensayo_sel, items_excel)
                                if items_nuevos:
                                    st.success(f"Se importaron {items_nuevos} items nuevos al ensayo {ensayo_sel}.")
                                else:
                                    st.info("Todos los items de ese protocolo ya estaban cargados en este ensayo.")
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
            total_items = int(len(df_items))
            total_completados = int(df_items["done"].fillna(False).astype(bool).sum())
            total_pendientes = total_items - total_completados
            progreso = (total_completados / total_items) if total_items else 0

            m1, m2, m3 = st.columns(3)
            with m1:
                st.metric("Total", total_items)
            with m2:
                st.metric("Completados", total_completados)
            with m3:
                st.metric("Pendientes", total_pendientes)

            st.progress(progreso, text=f"Progreso global: {total_completados}/{total_items}")

            grupos_checklist = agrupar_items_checklist(df_items)
            for bloque in grupos_checklist:
                items_bloque = bloque["items"]
                hechos_bloque = sum(1 for item in items_bloque if item["done"])
                total_bloque = len(items_bloque)
                titulo_bloque = f"{bloque['grupo']} · {hechos_bloque}/{total_bloque}"

                with st.expander(titulo_bloque, expanded=hechos_bloque < total_bloque):
                    progreso_bloque = (hechos_bloque / total_bloque) if total_bloque else 0
                    st.progress(progreso_bloque)

                    for item in items_bloque:
                        cols = st.columns([8, 1])
                        with cols[0]:
                            estado = st.checkbox(
                                item["titulo"],
                                value=item["done"],
                                key=f"chk_{item['id']}"
                            )
                            if item["detalle"]:
                                st.caption(item["detalle"])
                            if estado != item["done"]:
                                set_checklist_done(item["id"], estado)
                        with cols[1]:
                            if st.button("🗑️", key=f"del_{item['id']}"):
                                delete_checklist_item(item["id"])
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

if seccion_activa == "Notas coordinacion":
    st.subheader("🗂️ Notas de coordinación de ensayos")

    urgencias = {
        "verde": {"label": "Verde (baja)", "icono": "🟢", "color": "#15803d"},
        "amarillo": {"label": "Amarillo (media)", "icono": "🟡", "color": "#ca8a04"},
        "rojo": {"label": "Rojo (alta)", "icono": "🔴", "color": "#dc2626"},
    }

    with st.form("form_nota_coordinacion", clear_on_submit=True):
        fecha_nota = st.date_input("Fecha de la nota", value=fecha_hoy_local(), key="nota_coord_fecha")
        texto_nota = st.text_area("Texto libre", key="nota_coord_texto", height=120)
        urgencia_sel = st.selectbox(
            "Urgencia (semáforo)",
            options=list(urgencias.keys()),
            format_func=lambda u: f"{urgencias[u]['icono']} {urgencias[u]['label']}",
            key="nota_coord_urgencia"
        )
        guardar_nota = st.form_submit_button("Guardar nota", type="primary")

        if guardar_nota:
            texto_limpio = texto_nota.strip()
            if not texto_limpio:
                st.warning("El texto de la nota no puede estar vacio.")
            else:
                add_nota_coordinacion(fecha_nota.isoformat(), texto_limpio, urgencia_sel)
                st.success("Nota de coordinación guardada.")
                st.rerun()

    df_notas_coord = get_notas_coordinacion()
    if df_notas_coord.empty:
        st.info("No hay notas de coordinación pendientes.")
    else:
        st.caption("Marca una nota como realizada para eliminarla automáticamente.")
        for _, row in df_notas_coord.iterrows():
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
            if st.button("✅ Marcar como realizado (borrar)", key=f"nota_coord_done_{int(row['id'])}"):
                latencia_cierre = formatear_latencia_desde_creacion(row.get("creado_en"))
                delete_nota_coordinacion(int(row["id"]))
                st.success(f"Nota realizada y eliminada. Latencia de respuesta: {latencia_cierre}.")
                st.rerun()
            st.markdown("---")

if seccion_activa == "Adendas":
    st.subheader("📎 Adendas por paciente")

    ensayos = get_ensayos_existentes()
    if not ensayos:
        st.info("No hay ensayos guardados todavía. Registra visitas para habilitar adendas.")
    else:
        ensayo_sel = st.selectbox("Ensayo", options=ensayos, key="adenda_ensayo_sel")
        df_con_adenda = get_pacientes_con_adenda(ensayo_sel)
        if df_con_adenda.empty:
            st.info("Pacientes con adenda en este ensayo: ninguno")
        else:
            etiquetas_con_adenda = []
            for _, row in df_con_adenda.iterrows():
                codigo_ad = "" if pd.isna(row.get("codigo")) else str(row.get("codigo")).strip()
                nombre_ad = "" if pd.isna(row.get("nombre")) else str(row.get("nombre")).strip()
                etiqueta_ad = f"{codigo_ad} | {nombre_ad}".strip(" |")
                if etiqueta_ad:
                    etiquetas_con_adenda.append(etiqueta_ad)
            if etiquetas_con_adenda:
                st.success(
                    "Pacientes con adenda en este ensayo: "
                    + ", ".join(etiquetas_con_adenda)
                )
            else:
                st.info("Pacientes con adenda en este ensayo: ninguno")

        st.caption("Selecciona un paciente del ensayo para ver o guardar su adenda.")

        df_pacientes_ad = get_pacientes_unicos()
        if df_pacientes_ad.empty:
            st.info("No hay pacientes guardados para asociar adendas.")
        else:
            df_pacientes_ad = df_pacientes_ad.copy()
            for col in ["codigo", "nombre", "ensayo"]:
                if col not in df_pacientes_ad.columns:
                    df_pacientes_ad[col] = ""
                df_pacientes_ad[col] = df_pacientes_ad[col].fillna("").astype(str)

            pacientes_ensayo = df_pacientes_ad[
                df_pacientes_ad["ensayo"].astype(str) == str(ensayo_sel)
            ].copy()

            opciones_pac = []
            mapa_pac = {}
            for _, row in pacientes_ensayo.iterrows():
                codigo = str(row.get("codigo") or "").strip()
                nombre = str(row.get("nombre") or "").strip()
                ensayo = str(row.get("ensayo") or "").strip()
                etiqueta = f"{codigo} | {nombre}".strip(" |")
                if not etiqueta:
                    continue
                opciones_pac.append(etiqueta)
                mapa_pac[etiqueta] = {
                    "codigo": codigo,
                    "nombre": nombre,
                    "ensayo": ensayo,
                }

            if not opciones_pac:
                st.info("No hay pacientes en este ensayo para asociar adendas.")
            else:
                paciente_sel = st.selectbox(
                    "Paciente",
                    options=opciones_pac,
                    key=f"adenda_paciente_sel_{ensayo_sel}"
                )
                datos_sel = mapa_pac.get(paciente_sel, {})

                codigo_sel = datos_sel.get("codigo", "")
                nombre_sel = datos_sel.get("nombre", "")
                ensayo_pac = datos_sel.get("ensayo", "")
                adenda_pac_actual = get_adenda_paciente(codigo_sel, nombre_sel, ensayo_pac)

                with st.form(f"form_adenda_paciente_{normalizar_clave_paciente(ensayo_sel)}"):
                    texto_adenda_pac = st.text_area(
                        "Texto libre de la adenda del paciente",
                        value=adenda_pac_actual.get("texto", ""),
                        height=180,
                        key=f"adenda_paciente_texto_{normalizar_clave_paciente(codigo_sel)}_{normalizar_clave_paciente(ensayo_sel)}"
                    )
                    guardar_adenda_pac = st.form_submit_button("Guardar adenda paciente", type="primary")
                    if guardar_adenda_pac:
                        guardar_adenda_paciente(codigo_sel, nombre_sel, ensayo_pac, texto_adenda_pac.strip())
                        st.success("Adenda del paciente guardada.")
                        st.rerun()

                fecha_mod_pac = adenda_pac_actual.get("fecha_modificacion", "")
                if fecha_mod_pac:
                    st.caption(f"Última modificación adenda paciente: {fecha_mod_pac}")

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

                    adenda_paciente_info = get_adenda_paciente(
                        paciente.get('codigo'),
                        paciente.get('nombre'),
                        paciente.get('ensayo')
                    )
                    with st.expander("Adenda asociada al paciente", expanded=False):
                        with st.form(f"form_adenda_paciente_agenda_{id_evento_cmp}"):
                            texto_adenda_paciente = st.text_area(
                                "Texto libre",
                                value=adenda_paciente_info.get("texto", ""),
                                height=120,
                                key=f"agenda_adenda_paciente_{id_evento_cmp}"
                            )
                            guardar_adenda_paciente_btn = st.form_submit_button(
                                "Guardar adenda paciente",
                                type="primary"
                            )
                            if guardar_adenda_paciente_btn:
                                guardar_adenda_paciente(
                                    paciente.get('codigo'),
                                    paciente.get('nombre'),
                                    paciente.get('ensayo'),
                                    texto_adenda_paciente.strip()
                                )
                                st.success("Adenda del paciente guardada.")
                                st.rerun()

                        fecha_mod_pac = adenda_paciente_info.get("fecha_modificacion", "")
                        if fecha_mod_pac:
                            st.caption(f"Ultima modificación: {fecha_mod_pac}")

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
                    tab_medula, tab_kits, tab_otras, tab_comentarios, tab_ojos = st.tabs(
                        ["Médula/Tablet", "Kits", "Otras pruebas", "Comentarios", "Citas de ojos"]
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
                    with tab_ojos:
                        sedes_disponibles = ["cabueñes", "puerta de la villa", "pumarin"]
                        rev = get_revision_ocular(id_evento_cmp)
                        sede_actual = str(rev.get("sede") or "").strip().lower()
                        if sede_actual in sedes_disponibles:
                            sede_index = sedes_disponibles.index(sede_actual)
                        else:
                            sede_index = 0
                        medico_actual = str(rev.get("medico") or "").strip().upper()
                        medicos_disponibles = [""] + MEDICOS_OJOS_PERMITIDOS
                        if medico_actual in medicos_disponibles:
                            medico_index = medicos_disponibles.index(medico_actual)
                        else:
                            medico_index = 0

                        fecha_eval_default = parse_fecha_iso(rev.get("fecha_evaluacion"))
                        if fecha_eval_default is None:
                            fecha_eval_default = parse_fecha_iso(paciente['fecha']) or fecha_hoy_local()

                        with st.form(f"form_revision_{id_evento_cmp}"):
                            sede_sel = st.selectbox(
                                "Dónde",
                                options=sedes_disponibles,
                                index=sede_index,
                                format_func=lambda v: v.title(),
                            )
                            medico_sel = st.selectbox(
                                "Médico",
                                options=medicos_disponibles,
                                index=medico_index,
                            )
                            agenda_hospitalaria = st.text_area(
                                "Agenda hospitalaria (texto libre)",
                                value=rev.get("agenda_hospitalaria", ""),
                                height=90,
                            )
                            fecha_eval = st.date_input(
                                "Fecha de la evaluación",
                                value=fecha_eval_default,
                            )
                            resultado_eval = st.text_area(
                                "Resultado",
                                value=rev.get("resultado", ""),
                                height=90,
                            )
                            guardar_rev = st.form_submit_button("Guardar cita de ojos", type="primary")
                            if guardar_rev:
                                guardar_revision_ocular(
                                    id_evento_cmp,
                                    sede_sel,
                                    medico_sel,
                                    agenda_hospitalaria,
                                    fecha_eval.isoformat(),
                                    resultado_eval,
                                )
                                st.success("Cita de ojos guardada.")
                                st.rerun()

                    rev_informe = get_revision_ocular(id_evento_cmp)

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
                        f"Revision ocular (sede): {rev_informe.get('sede', '')}\n"
                        f"Medico ocular: {rev_informe.get('medico', '')}\n"
                        f"Agenda hospitalaria ocular: {rev_informe.get('agenda_hospitalaria', '')}\n"
                        f"Fecha evaluacion ocular: {formatear_fecha_visita(rev_informe.get('fecha_evaluacion', ''))}\n"
                        f"Resultado ocular: {rev_informe.get('resultado', '')}\n"
                        f"Adenda paciente: {adenda_paciente_info.get('texto', '')}\n"
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

