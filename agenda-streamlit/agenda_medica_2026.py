import streamlit as st
from streamlit_calendar import calendar
import sqlite3
from datetime import datetime
import pandas as pd
from pathlib import Path

DB_PATH = Path(__file__).with_name("agenda_ensayos.db")

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Agenda Ensayos 2026", layout="wide")

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
if 'mostrar_portada' not in st.session_state:
    st.session_state['mostrar_portada'] = True

# --- BASE DE DATOS ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
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
    conn.commit()
    conn.close()

def guardar_visita(fecha, data):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO visitas (fecha, nombre, codigo, ensayo, ciclo, kits, tablet, medula, otras_pruebas, comentarios)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (fecha, data['nombre'], data['codigo'], data['ensayo'], data['ciclo'], 
          data['kits'], data['tablet'], data['medula'], data['otras_pruebas'], data['comentarios']))
    conn.commit()
    conn.close()

def get_visitas():
    conn = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql("SELECT * FROM visitas", conn)
    except:
        df = pd.DataFrame()
    conn.close()
    return df

def get_pacientes_unicos():
    df = get_visitas()
    if df.empty:
        return pd.DataFrame()
    return df[['codigo', 'nombre', 'ensayo']].dropna(how='all').drop_duplicates()

def borrar_visita(id_visita):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM visitas WHERE id=?", (id_visita,))
    conn.commit()
    conn.close()

# Inicializamos DB
init_db()

# --- PORTADA ---
if st.session_state['mostrar_portada']:
    st.title("📘 Agenda de Pacientes 2026")
    st.subheader("Ensayos Clínicos")
    st.write("Sistema para organizar y consultar visitas de pacientes.")
    if st.button("Entrar a la agenda", type="primary"):
        st.session_state['mostrar_portada'] = False
        st.rerun()
    st.stop()

# --- INTERFAZ PRINCIPAL ---
st.title("📅 Agenda de Pacientes - Ensayos Clínicos 2026")

col_cal, col_detalles = st.columns([2, 1])

# 1. Preparar eventos para el calendario
df_visitas = get_visitas()
calendar_events = []

if not df_visitas.empty:
    for index, row in df_visitas.iterrows():
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
                "ensayo": row['ensayo'] # Guardamos datos clave para visualización rápida
            },
            # Color diferente si lleva médula
            "backgroundColor": "#ff4b4b" if row['medula'] else "#3788d8"
        }
        calendar_events.append(event)

# 2. Configuración del Calendario
calendar_options = {
    "editable": True,
    "navLinks": True,
    "headerToolbar": {
        "left": "today prev,next",
        "center": "title",
        "right": "dayGridMonth,listDay"
    },
    "initialDate": "2026-01-01",
    "firstDay": 1,
    "selectable": True,
}

with col_cal:
    calendar_state = calendar(events=calendar_events, options=calendar_options, key="mi_calendario")

if calendar_state is None:
    calendar_state = {}

# --- LÓGICA DE DETECCIÓN DE CLICS ---
# Si se hace clic en el calendario, actualizamos la memoria (Session State)
if calendar_state.get("dateClick"):
    st.session_state['modo_formulario'] = 'nuevo'
    st.session_state['datos_seleccionados'] = calendar_state["dateClick"]["date"]

elif calendar_state.get("eventClick"):
    st.session_state['modo_formulario'] = 'ver'
    # Guardamos el ID del evento clickado
    props = calendar_state["eventClick"]["event"]["extendedProps"]
    st.session_state['datos_seleccionados'] = props["id"]

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
            
            ensayo = st.text_input("Ensayo / Protocolo", key="ensayo_input")
            ciclo = st.text_input("Ciclo / Día (Ej. C1D1)")
            
            st.divider()
            kits = st.text_input("Kits / Medicación")
            
            cc1, cc2 = st.columns(2)
            tablet = cc1.checkbox("Requiere Tablet")
            medula = cc2.checkbox("🩸 Punción Médula")
            
            otras = st.text_area("Otras pruebas")
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

                st.info(f"📅 Fecha: {paciente['fecha']}")
                st.markdown(f"## 🆔 {paciente['codigo']}")
                st.markdown(f"**Paciente:** {paciente['nombre']}")
                st.markdown(f"**Ensayo:** {paciente['ensayo']} | **Ciclo:** {paciente['ciclo']}")

                st.divider()
                if paciente['medula']:
                    st.error("🩸 **Requiere Médula Ósea**")
                if paciente['tablet']:
                    st.warning("📱 **Preparar Tablet**")

                st.write(f"**Kits:** {paciente['kits']}")
                st.write(f"**Notas:** {paciente['comentarios']}")
                st.caption(f"Otras pruebas: {paciente['otras_pruebas']}")

                informe = (
                    f"Informe de visita\n"
                    f"Fecha: {paciente['fecha']}\n"
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
                    file_name=f"informe_{paciente['codigo']}_{paciente['fecha']}.txt",
                    mime="text/plain"
                )

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