import os
import re
from pathlib import Path

import pandas as pd


ARCHIVO_CATALOGO_TIPOS = "catalogo_tipos_por_ensayo.csv"
ARCHIVO_CATALOGO_CICLOS = "catalogo_kits_por_ciclo.csv"
TABLA_CATALOGO_TIPOS = "catalogo_tipos_por_ensayo"
TABLA_CATALOGO_CICLOS = "catalogo_kits_por_ciclo"

COLUMNAS_CATALOGO_TIPOS = ["Ensayo", "Tipo de kit"]
COLUMNAS_CATALOGO_CICLOS = ["Ensayo", "Ciclo", "Tipo de kit"]


def _normalizar_texto(valor) -> str:
    if valor is None:
        return ""
    txt = str(valor).strip()
    txt = re.sub(r"\s+", " ", txt)
    return txt


def normalizar_ensayo(valor) -> str:
    return _normalizar_texto(valor).upper()


def normalizar_ciclo(valor) -> str:
    ciclo = _normalizar_texto(valor).upper()
    return re.sub(r"[\s\-_\/]+", "", ciclo)


def normalizar_tipo_kit(valor) -> str:
    return _normalizar_texto(valor)


def limpiar_catalogo_tipos(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=COLUMNAS_CATALOGO_TIPOS)
    out = df.copy()
    for col in COLUMNAS_CATALOGO_TIPOS:
        if col not in out.columns:
            out[col] = ""
    out["Ensayo"] = out["Ensayo"].apply(normalizar_ensayo)
    out["Tipo de kit"] = out["Tipo de kit"].apply(normalizar_tipo_kit)
    out = out[(out["Ensayo"] != "") & (out["Tipo de kit"] != "")]
    out = out.drop_duplicates(subset=["Ensayo", "Tipo de kit"]).reset_index(drop=True)
    return out[COLUMNAS_CATALOGO_TIPOS].copy()


def limpiar_catalogo_ciclos(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=COLUMNAS_CATALOGO_CICLOS)
    out = df.copy()
    for col in COLUMNAS_CATALOGO_CICLOS:
        if col not in out.columns:
            out[col] = ""
    out["Ensayo"] = out["Ensayo"].apply(normalizar_ensayo)
    out["Ciclo"] = out["Ciclo"].apply(normalizar_ciclo)
    out["Tipo de kit"] = out["Tipo de kit"].apply(normalizar_tipo_kit)
    out = out[(out["Ensayo"] != "") & (out["Ciclo"] != "") & (out["Tipo de kit"] != "")]
    out = out.drop_duplicates(subset=["Ensayo", "Ciclo"], keep="last").reset_index(drop=True)
    return out[COLUMNAS_CATALOGO_CICLOS].copy()


def resolver_tipo_kit(ensayo, ciclo, catalogo_ciclos: pd.DataFrame, catalogo_tipos: pd.DataFrame) -> str:
    ensayo_norm = normalizar_ensayo(ensayo)
    ciclo_norm = normalizar_ciclo(ciclo)
    if not ensayo_norm:
        return ""

    ciclos = limpiar_catalogo_ciclos(catalogo_ciclos)
    if not ciclos.empty and ciclo_norm:
        match = ciclos[
            (ciclos["Ensayo"] == ensayo_norm)
            & (ciclos["Ciclo"] == ciclo_norm)
        ]
        if not match.empty:
            return str(match.iloc[0]["Tipo de kit"]).strip()

    tipos = limpiar_catalogo_tipos(catalogo_tipos)
    if tipos.empty:
        return ""
    match_tipos = tipos[tipos["Ensayo"] == ensayo_norm]
    if match_tipos.empty:
        return ""
    return str(match_tipos.iloc[0]["Tipo de kit"]).strip()


def _leer_csv(path: str, columnas: list[str]) -> pd.DataFrame:
    if not os.path.exists(path):
        return pd.DataFrame(columns=columnas)
    try:
        df = pd.read_csv(path, dtype=str)
    except Exception:
        return pd.DataFrame(columns=columnas)
    for col in columnas:
        if col not in df.columns:
            df[col] = ""
    return df[columnas].fillna("").astype(str)


def cargar_catalogos_desde_csv(base_dir: str | Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    base = Path(base_dir)
    ciclos = _leer_csv(str(base / ARCHIVO_CATALOGO_CICLOS), COLUMNAS_CATALOGO_CICLOS)
    tipos = _leer_csv(str(base / ARCHIVO_CATALOGO_TIPOS), COLUMNAS_CATALOGO_TIPOS)
    return limpiar_catalogo_ciclos(ciclos), limpiar_catalogo_tipos(tipos)


def cargar_catalogos_desde_postgres(database_url: str, psycopg2_mod) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not database_url or psycopg2_mod is None:
        return (
            pd.DataFrame(columns=COLUMNAS_CATALOGO_CICLOS),
            pd.DataFrame(columns=COLUMNAS_CATALOGO_TIPOS),
        )
    try:
        with psycopg2_mod.connect(database_url, connect_timeout=10) as conn:
            with conn.cursor() as cur:
                cur.execute(f"SELECT ensayo, ciclo, tipo_de_kit FROM {TABLA_CATALOGO_CICLOS}")
                ciclos_rows = cur.fetchall()
                cur.execute(f"SELECT ensayo, tipo_de_kit FROM {TABLA_CATALOGO_TIPOS}")
                tipos_rows = cur.fetchall()
    except Exception:
        return (
            pd.DataFrame(columns=COLUMNAS_CATALOGO_CICLOS),
            pd.DataFrame(columns=COLUMNAS_CATALOGO_TIPOS),
        )

    ciclos = pd.DataFrame(ciclos_rows, columns=["Ensayo", "Ciclo", "Tipo de kit"])
    tipos = pd.DataFrame(tipos_rows, columns=["Ensayo", "Tipo de kit"])
    return limpiar_catalogo_ciclos(ciclos), limpiar_catalogo_tipos(tipos)
