"""
AEs / Síntomas + Medicación — registro clínico compacto para ensayos.

Interfaz de escritorio en Streamlit: cuadrícula de AEs con interruptor ON/OFF,
modal de grado CTCAE + medicación, tabla de AEs activos e histórico completo.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="AEs / Síntomas + Medicación",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --------------------------------------------------------------------------
# Datos: catálogo de AEs y modelos
# --------------------------------------------------------------------------

CATALOGO_AES = [
    "Fatiga", "Náuseas", "Cefalea", "Diarrea",
    "Rash", "Neuropatía periférica", "Fiebre", "Infección",
    "Dolor óseo", "Mucositis", "Edema", "CRS",
    "ICANS", "Estreñimiento", "Hipotensión", "Hipertensión",
]

GRADOS = ["G1", "G2", "G3", "G4", "G5"]

GRADO_COLOR = {
    "G1": ("#6b7280", "#f3f4f6"),   # gris
    "G2": ("#b45309", "#fef3c7"),  # ámbar discreto
    "G3": ("#c2410c", "#ffedd5"),  # naranja
    "G4": ("#b91c1c", "#fee2e2"),  # rojo
    "G5": ("#991b1b", "#fecaca"),  # rojo fuerte
}


@dataclass
class Medicacion:
    id: str
    nombre: str = ""
    dosis: str = ""
    pauta: str = ""
    ruta: str = ""


@dataclass
class RegistroAE:
    id: str
    nombre: str
    gradoCTCAE: Optional[str] = None
    activo: bool = False
    fechaInicio: Optional[datetime] = None
    fechaFin: Optional[datetime] = None
    medicaciones: list = field(default_factory=list)


def _init_state():
    if "ae_records" in st.session_state:
        return

    records = []

    # Ejemplo activo requerido por spec: Náuseas G2, Ondansetrón 8mg c/8h VO
    records.append(
        RegistroAE(
            id=str(uuid.uuid4()),
            nombre="Náuseas",
            gradoCTCAE="G2",
            activo=True,
            fechaInicio=datetime(2026, 8, 13, 9, 0),
            fechaFin=None,
            medicaciones=[
                Medicacion(id=str(uuid.uuid4()), nombre="Ondansetrón", dosis="8 mg", pauta="cada 8 h", ruta="VO"),
            ],
        )
    )
    records.append(
        RegistroAE(
            id=str(uuid.uuid4()),
            nombre="Cefalea",
            gradoCTCAE="G1",
            activo=False,
            fechaInicio=datetime(2026, 8, 10, 10, 0),
            fechaFin=datetime(2026, 8, 11, 18, 0),
            medicaciones=[
                Medicacion(id=str(uuid.uuid4()), nombre="Paracetamol", dosis="1 g", pauta="si dolor", ruta="VO"),
            ],
        )
    )

    st.session_state.ae_records = records
    st.session_state.pending_edit_id = None
    st.session_state.pending_deactivate_id = None


_init_state()


def get_active_record(nombre: str) -> Optional[RegistroAE]:
    for r in st.session_state.ae_records:
        if r.nombre == nombre and r.activo:
            return r
    return None


def get_record(record_id: str) -> Optional[RegistroAE]:
    for r in st.session_state.ae_records:
        if r.id == record_id:
            return r
    return None


def fmt_date(dt: Optional[datetime], with_time: bool = False) -> str:
    if dt is None:
        return "—"
    return dt.strftime("%d/%m/%Y %H:%M" if with_time else "%d/%m/%Y")


def grade_badge(grado: Optional[str]) -> str:
    if not grado:
        return '<span style="color:#9ca3af;">—</span>'
    color, bg = GRADO_COLOR.get(grado, ("#6b7280", "#f3f4f6"))
    return (
        f'<span style="background:{bg}; color:{color}; padding:2px 8px; '
        f'border-radius:6px; font-weight:600; font-size:0.8rem;">{grado}</span>'
    )


# --------------------------------------------------------------------------
# Estilos: minimalista, tipo dashboard clínico
# --------------------------------------------------------------------------

st.markdown(
    """
    <style>
        .block-container { padding-top: 1.6rem; padding-bottom: 3rem; max-width: 1400px; }
        h1, h2, h3 { letter-spacing: -0.01em; }
        div[data-testid="stToggle"] {
            border: 1px solid #e5e7eb;
            border-radius: 10px;
            padding: 8px 12px;
            background: #fafafa;
            transition: all .12s ease;
        }
        div[data-testid="stToggle"]:has(input:checked) {
            border-color: #86efac;
            background: #f0fdf4;
        }
        div[data-testid="stToggle"] label p {
            font-weight: 500;
            color: #374151;
            font-size: 0.92rem;
        }
        div[data-testid="stToggle"]:has(input:checked) label p {
            color: #15803d;
        }
        .ae-section-title {
            font-size: 0.82rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            color: #6b7280;
            margin: 1.6rem 0 0.5rem 0;
        }
        .ae-row {
            border-bottom: 1px solid #f1f5f9;
            padding: 6px 0;
        }
        .ae-row-header {
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            color: #9ca3af;
            border-bottom: 1px solid #e5e7eb;
            padding-bottom: 6px;
        }
        .ae-name-cell { font-weight: 600; color: #111827; }
        .ae-empty { color: #9ca3af; font-style: italic; padding: 0.8rem 0; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("AEs / Síntomas + medicación")

tab_registro, tab_historico = st.tabs(["Registro", "Histórico"])


# --------------------------------------------------------------------------
# Modal: activar / editar AE (grado + medicación)
# --------------------------------------------------------------------------

@st.dialog("Registro de AE")
def render_ae_dialog(record_id: str):
    record = get_record(record_id)
    if record is None:
        st.session_state.pending_edit_id = None
        st.rerun()
        return

    if record.nombre == "Otro":
        record.nombre = st.text_input("Nombre del AE", value=record.nombre or "")

    st.subheader(record.nombre or "(sin nombre)")

    grado = st.radio(
        "Grado CTCAE",
        GRADOS,
        index=GRADOS.index(record.gradoCTCAE) if record.gradoCTCAE in GRADOS else None,
        horizontal=True,
        key=f"grado_{record.id}",
    )

    st.markdown("**¿Tratamiento para este AE?**")
    draft_key = f"meds_draft_{record.id}"
    if draft_key not in st.session_state:
        st.session_state[draft_key] = [
            {"id": m.id, "nombre": m.nombre, "dosis": m.dosis, "pauta": m.pauta, "ruta": m.ruta}
            for m in record.medicaciones
        ]

    tto_default = "Sí" if st.session_state[draft_key] else "No"
    tto = st.radio(
        "tto", ["Sí", "No"], index=["Sí", "No"].index(tto_default),
        horizontal=True, key=f"tto_{record.id}", label_visibility="collapsed",
    )

    if tto == "Sí":
        to_remove = None
        for i, med in enumerate(st.session_state[draft_key]):
            cols = st.columns([2.2, 1, 1.4, 1, 0.4])
            med["nombre"] = cols[0].text_input("Medicamento", value=med["nombre"], key=f"{draft_key}_{i}_nombre")
            med["dosis"] = cols[1].text_input("Dosis", value=med["dosis"], key=f"{draft_key}_{i}_dosis")
            med["pauta"] = cols[2].text_input("Pauta", value=med["pauta"], key=f"{draft_key}_{i}_pauta")
            med["ruta"] = cols[3].text_input("Ruta", value=med["ruta"], key=f"{draft_key}_{i}_ruta")
            cols[4].markdown("&nbsp;")
            if cols[4].button("🗑", key=f"{draft_key}_{i}_del"):
                to_remove = i
        if to_remove is not None:
            st.session_state[draft_key].pop(to_remove)
            st.rerun()

        if st.button("+ Añadir medicación", key=f"{draft_key}_add"):
            st.session_state[draft_key].append(
                {"id": str(uuid.uuid4()), "nombre": "", "dosis": "", "pauta": "", "ruta": ""}
            )
            st.rerun()

    st.divider()
    c1, c2 = st.columns([1, 1])
    if c1.button("Cancelar", use_container_width=True):
        # Si era una activación recién creada sin datos, se descarta el registro
        if record.gradoCTCAE is None and not record.medicaciones:
            st.session_state.ae_records = [r for r in st.session_state.ae_records if r.id != record.id]
        del st.session_state[draft_key]
        st.session_state.pending_edit_id = None
        st.rerun()

    if c2.button("Guardar AE", type="primary", use_container_width=True):
        if not grado:
            st.error("Selecciona un grado CTCAE.")
        elif not record.nombre.strip():
            st.error("Indica el nombre del AE.")
        else:
            record.gradoCTCAE = grado
            if tto == "Sí":
                record.medicaciones = [
                    Medicacion(id=m["id"], nombre=m["nombre"], dosis=m["dosis"], pauta=m["pauta"], ruta=m["ruta"])
                    for m in st.session_state[draft_key]
                    if m["nombre"].strip()
                ]
            else:
                record.medicaciones = []
            del st.session_state[draft_key]
            st.session_state.pending_edit_id = None
            st.rerun()


@st.dialog("Confirmar")
def render_confirm_off_dialog(record_id: str):
    record = get_record(record_id)
    if record is None:
        st.session_state.pending_deactivate_id = None
        st.rerun()
        return

    st.write(f"¿Marcar **{record.nombre}** como resuelto?")
    c1, c2 = st.columns(2)
    if c1.button("Cancelar", use_container_width=True):
        st.session_state[f"tgl_{record.nombre}"] = True
        st.session_state.pending_deactivate_id = None
        st.rerun()
    if c2.button("Confirmar", type="primary", use_container_width=True):
        record.activo = False
        record.fechaFin = datetime.now()
        st.session_state.pending_deactivate_id = None
        st.rerun()


# --------------------------------------------------------------------------
# Tab Registro
# --------------------------------------------------------------------------

with tab_registro:
    st.markdown('<div class="ae-section-title">AEs / Síntomas</div>', unsafe_allow_html=True)

    n_cols = 4
    rows = [CATALOGO_AES[i:i + n_cols] for i in range(0, len(CATALOGO_AES), n_cols)]

    for row in rows:
        cols = st.columns(n_cols)
        for col, nombre in zip(cols, row):
            with col:
                active_rec = get_active_record(nombre)
                is_on = active_rec is not None
                new_val = st.toggle(nombre, value=is_on, key=f"tgl_{nombre}")
                if new_val and not is_on:
                    new_rec = RegistroAE(
                        id=str(uuid.uuid4()),
                        nombre=nombre,
                        activo=True,
                        fechaInicio=datetime.now(),
                    )
                    st.session_state.ae_records.append(new_rec)
                    st.session_state.pending_edit_id = new_rec.id
                elif not new_val and is_on:
                    st.session_state.pending_deactivate_id = active_rec.id

    # Chip especial "+ Otro"
    if st.button("+ Otro", key="btn_otro"):
        new_rec = RegistroAE(id=str(uuid.uuid4()), nombre="Otro", activo=True, fechaInicio=datetime.now())
        st.session_state.ae_records.append(new_rec)
        st.session_state.pending_edit_id = new_rec.id

    if st.session_state.pending_edit_id:
        render_ae_dialog(st.session_state.pending_edit_id)
    if st.session_state.pending_deactivate_id:
        render_confirm_off_dialog(st.session_state.pending_deactivate_id)

    st.markdown('<div class="ae-section-title">AEs activos</div>', unsafe_allow_html=True)

    activos = [r for r in st.session_state.ae_records if r.activo]

    if not activos:
        st.markdown('<div class="ae-empty">No hay AEs activos.</div>', unsafe_allow_html=True)
    else:
        ratios = [1.1, 0.6, 0.9, 1.4, 1.0, 1.1, 0.7, 0.7]
        headers = ["AE", "Grado", "Inicio", "Medicación", "Dosis", "Pauta", "Ruta", "Acción"]
        hcols = st.columns(ratios)
        for c, h in zip(hcols, headers):
            c.markdown(f'<div class="ae-row-header">{h}</div>', unsafe_allow_html=True)

        for r in activos:
            cols = st.columns(ratios)
            meds = r.medicaciones or [Medicacion(id="", nombre="—", dosis="—", pauta="—", ruta="—")]
            cols[0].markdown(f'<div class="ae-row ae-name-cell">{r.nombre}</div>', unsafe_allow_html=True)
            cols[1].markdown(f'<div class="ae-row">{grade_badge(r.gradoCTCAE)}</div>', unsafe_allow_html=True)
            cols[2].markdown(f'<div class="ae-row">{fmt_date(r.fechaInicio)}</div>', unsafe_allow_html=True)
            cols[3].markdown(f'<div class="ae-row">{"<br>".join(m.nombre for m in meds)}</div>', unsafe_allow_html=True)
            cols[4].markdown(f'<div class="ae-row">{"<br>".join(m.dosis for m in meds)}</div>', unsafe_allow_html=True)
            cols[5].markdown(f'<div class="ae-row">{"<br>".join(m.pauta for m in meds)}</div>', unsafe_allow_html=True)
            cols[6].markdown(f'<div class="ae-row">{"<br>".join(m.ruta for m in meds)}</div>', unsafe_allow_html=True)
            with cols[7]:
                st.markdown('<div class="ae-row">', unsafe_allow_html=True)
                if st.button("Editar", key=f"edit_{r.id}"):
                    st.session_state.pending_edit_id = r.id
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)


# --------------------------------------------------------------------------
# Tab Histórico
# --------------------------------------------------------------------------

with tab_historico:
    st.markdown('<div class="ae-section-title">Histórico completo</div>', unsafe_allow_html=True)

    records = st.session_state.ae_records
    if not records:
        st.markdown('<div class="ae-empty">Aún no hay registros.</div>', unsafe_allow_html=True)
    else:
        data = []
        for r in sorted(records, key=lambda x: x.fechaInicio or datetime.min, reverse=True):
            meds = r.medicaciones
            data.append(
                {
                    "AE": r.nombre,
                    "Grado CTCAE": r.gradoCTCAE or "—",
                    "Inicio": fmt_date(r.fechaInicio),
                    "Fin": fmt_date(r.fechaFin),
                    "Estado": "Activo" if r.activo else "Resuelto",
                    "Medicación": "; ".join(m.nombre for m in meds) or "—",
                    "Dosis": "; ".join(m.dosis for m in meds) or "—",
                    "Pauta": "; ".join(m.pauta for m in meds) or "—",
                    "Ruta": "; ".join(m.ruta for m in meds) or "—",
                }
            )
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)
