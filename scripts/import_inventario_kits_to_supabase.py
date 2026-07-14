#!/usr/bin/env python3
"""Import inventario_kits.csv into Supabase/PostgreSQL.

Usage:
  DATABASE_URL='postgresql://...' python scripts/import_inventario_kits_to_supabase.py inventario_kits.csv

If DATABASE_URL is not set in the environment, the script also tries:
  - .streamlit/secrets.toml
  - agenda-streamlit/.streamlit/secrets.toml
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import pandas as pd
import psycopg2
import psycopg2.extras

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None


ROOT_DIR = Path(__file__).resolve().parent.parent
SECRETS_CANDIDATES = [
    ROOT_DIR / ".streamlit" / "secrets.toml",
    ROOT_DIR / "agenda-streamlit" / ".streamlit" / "secrets.toml",
]

TARGET_TABLE = "inventario_kits"
TARGET_COLUMNS = ["codigo_barras", "ensayo", "tipo_de_kit", "caducidad"]
CSV_COLUMN_MAP = {
    "codigo de barras": "codigo_barras",
    "codigo_barras": "codigo_barras",
    "codigo barras": "codigo_barras",
    "ensayo": "ensayo",
    "tipo de kit": "tipo_de_kit",
    "tipo_de_kit": "tipo_de_kit",
    "caducidad": "caducidad",
}


def _read_toml(path: Path) -> dict:
    if tomllib is None or not path.exists():
        return {}
    try:
        with path.open("rb") as handle:
            return tomllib.load(handle)
    except Exception:
        return {}


def load_database_url() -> str:
    env_url = (os.getenv("DATABASE_URL") or "").strip()
    if env_url:
        return env_url

    for secrets_path in SECRETS_CANDIDATES:
        data = _read_toml(secrets_path)
        url = str(data.get("DATABASE_URL") or "").strip()
        if url:
            return url

    return ""


def ensure_schema(cur) -> None:
    cur.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {TARGET_TABLE} (
            id BIGSERIAL PRIMARY KEY,
            codigo_barras TEXT NOT NULL UNIQUE,
            ensayo TEXT NOT NULL,
            tipo_de_kit TEXT NOT NULL,
            caducidad TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )


def normalize_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")

    df = pd.read_csv(path, dtype=str).fillna("")
    rename_map = {}
    for col in df.columns:
        key = str(col).strip().lower()
        if key in CSV_COLUMN_MAP:
            rename_map[col] = CSV_COLUMN_MAP[key]

    df = df.rename(columns=rename_map)

    missing = [col for col in TARGET_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"CSV is missing required columns: {', '.join(missing)}")

    out = df[TARGET_COLUMNS].copy()
    for col in TARGET_COLUMNS:
        out[col] = out[col].fillna("").astype(str).str.strip()

    out = out[out["codigo_barras"] != ""].copy()
    out = out.drop_duplicates(subset=["codigo_barras"], keep="last").reset_index(drop=True)
    return out


def upsert_inventory(conn, df: pd.DataFrame, replace: bool) -> int:
    with conn.cursor() as cur:
        ensure_schema(cur)
        if replace:
            cur.execute(f"TRUNCATE TABLE {TARGET_TABLE}")

        if df.empty:
            conn.commit()
            return 0

        rows = [tuple(row[col] for col in TARGET_COLUMNS) for _, row in df.iterrows()]
        query = f"""
            INSERT INTO {TARGET_TABLE} ({', '.join(TARGET_COLUMNS)})
            VALUES %s
            ON CONFLICT (codigo_barras) DO UPDATE SET
                ensayo = EXCLUDED.ensayo,
                tipo_de_kit = EXCLUDED.tipo_de_kit,
                caducidad = EXCLUDED.caducidad
        """
        psycopg2.extras.execute_values(cur, query, rows, page_size=500)
        conn.commit()
        return len(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Import inventario_kits.csv into Supabase/PostgreSQL")
    parser.add_argument("csv_path", help="Path to inventario_kits.csv")
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Truncate inventario_kits before importing",
    )
    args = parser.parse_args()

    database_url = load_database_url()
    if not database_url:
        print("ERROR: DATABASE_URL not found in env or secrets.toml")
        return 1

    csv_path = Path(args.csv_path).expanduser().resolve()
    try:
        df = normalize_csv(csv_path)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    try:
        conn = psycopg2.connect(database_url, connect_timeout=10)
    except Exception as exc:
        print(f"ERROR: Unable to connect to PostgreSQL: {exc}")
        return 1

    try:
        total = upsert_inventory(conn, df, replace=args.replace)
    except Exception as exc:
        conn.rollback()
        print(f"ERROR: Import failed: {exc}")
        return 1
    finally:
        conn.close()

    print(f"Imported {total} rows into {TARGET_TABLE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
