#!/usr/bin/env python3
"""Migrate local SQLite data (agenda_ensayos.db) into PostgreSQL.

Usage:
  DATABASE_URL='postgresql://...' python scripts/migrate_sqlite_to_postgres.py

If DATABASE_URL is not set in env, the script tries to read it from:
  - .streamlit/secrets.toml
  - agenda-streamlit/.streamlit/secrets.toml
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import psycopg2
import psycopg2.extras

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None


ROOT_DIR = Path(__file__).resolve().parent.parent
SQLITE_PATH = ROOT_DIR / "agenda_ensayos.db"
SECRETS_CANDIDATES = [
    ROOT_DIR / ".streamlit" / "secrets.toml",
    ROOT_DIR / "agenda-streamlit" / ".streamlit" / "secrets.toml",
]


def _read_toml(path: Path) -> dict:
    if tomllib is None:
        return {}
    if not path.exists():
        return {}
    try:
        with path.open("rb") as f:
            return tomllib.load(f)
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


def ensure_postgres_schema(pg_cur) -> None:
    pg_cur.execute(
        """
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
        """
    )
    pg_cur.execute(
        """
        CREATE TABLE IF NOT EXISTS revision_ocular (
            id BIGSERIAL PRIMARY KEY,
            visita_id BIGINT UNIQUE,
            fecha_cita TEXT,
            kva INTEGER
        )
        """
    )
    pg_cur.execute(
        """
        CREATE TABLE IF NOT EXISTS pacientes (
            id BIGSERIAL PRIMARY KEY,
            codigo TEXT,
            nombre TEXT,
            ensayo TEXT,
            UNIQUE(codigo, ensayo)
        )
        """
    )
    pg_cur.execute(
        """
        CREATE TABLE IF NOT EXISTS checklist_items (
            id BIGSERIAL PRIMARY KEY,
            ensayo TEXT,
            item TEXT,
            done BOOLEAN DEFAULT FALSE
        )
        """
    )
    pg_cur.execute(
        """
        CREATE TABLE IF NOT EXISTS notas_esquemas (
            id BIGSERIAL PRIMARY KEY,
            nombre_esquema TEXT UNIQUE,
            nota TEXT,
            fecha_modificacion TEXT
        )
        """
    )
    pg_cur.execute(
        """
        CREATE TABLE IF NOT EXISTS notas_enfermeria (
            id BIGSERIAL PRIMARY KEY,
            fecha_nota TEXT NOT NULL,
            texto TEXT NOT NULL,
            urgencia TEXT NOT NULL,
            creado_en TEXT NOT NULL
        )
        """
    )


def fetch_all(sqlite_cur, table: str, columns: list[str]) -> list[tuple]:
    query = f"SELECT {', '.join(columns)} FROM {table}"
    rows = sqlite_cur.execute(query).fetchall()
    return [tuple(row[col] for col in columns) for row in rows]


def upsert_table(pg_cur, table: str, columns: list[str], rows: list[tuple]) -> None:
    if not rows:
        return

    col_csv = ", ".join(columns)
    assignments = ", ".join([f"{c} = EXCLUDED.{c}" for c in columns if c != "id"])
    query = (
        f"INSERT INTO {table} ({col_csv}) VALUES %s "
        f"ON CONFLICT (id) DO UPDATE SET {assignments}"
    )
    psycopg2.extras.execute_values(pg_cur, query, rows, page_size=500)


def reset_sequence(pg_cur, table: str) -> None:
    # Keep BIGSERIAL sequences aligned after inserting explicit IDs.
    pg_cur.execute(
        f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
        f"COALESCE((SELECT MAX(id) FROM {table}), 1), true)"
    )


def main() -> int:
    if not SQLITE_PATH.exists():
        print(f"ERROR: SQLite file not found: {SQLITE_PATH}")
        return 1

    database_url = load_database_url()
    if not database_url:
        print("ERROR: DATABASE_URL not found in env or secrets.toml")
        return 1

    print(f"SQLite source: {SQLITE_PATH}")
    print("Connecting to PostgreSQL...")

    sqlite_conn = sqlite3.connect(str(SQLITE_PATH))
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()

    pg_conn = psycopg2.connect(database_url, connect_timeout=10)
    pg_cur = pg_conn.cursor()

    try:
        ensure_postgres_schema(pg_cur)

        visitas = fetch_all(
            sqlite_cur,
            "visitas",
            [
                "id",
                "fecha",
                "nombre",
                "codigo",
                "ensayo",
                "ciclo",
                "kits",
                "tablet",
                "medula",
                "otras_pruebas",
                "comentarios",
            ],
        )
        revision = fetch_all(
            sqlite_cur,
            "revision_ocular",
            ["id", "visita_id", "fecha_cita", "kva"],
        )
        pacientes = fetch_all(
            sqlite_cur,
            "pacientes",
            ["id", "codigo", "nombre", "ensayo"],
        )
        checklist = fetch_all(
            sqlite_cur,
            "checklist_items",
            ["id", "ensayo", "item", "done"],
        )
        notas_esquemas = fetch_all(
            sqlite_cur,
            "notas_esquemas",
            ["id", "nombre_esquema", "nota", "fecha_modificacion"],
        )
        notas_enf = fetch_all(
            sqlite_cur,
            "notas_enfermeria",
            ["id", "fecha_nota", "texto", "urgencia", "creado_en"],
        )

        upsert_table(
            pg_cur,
            "visitas",
            [
                "id",
                "fecha",
                "nombre",
                "codigo",
                "ensayo",
                "ciclo",
                "kits",
                "tablet",
                "medula",
                "otras_pruebas",
                "comentarios",
            ],
            visitas,
        )
        upsert_table(
            pg_cur,
            "revision_ocular",
            ["id", "visita_id", "fecha_cita", "kva"],
            revision,
        )
        upsert_table(
            pg_cur,
            "pacientes",
            ["id", "codigo", "nombre", "ensayo"],
            pacientes,
        )
        upsert_table(
            pg_cur,
            "checklist_items",
            ["id", "ensayo", "item", "done"],
            checklist,
        )
        upsert_table(
            pg_cur,
            "notas_esquemas",
            ["id", "nombre_esquema", "nota", "fecha_modificacion"],
            notas_esquemas,
        )
        upsert_table(
            pg_cur,
            "notas_enfermeria",
            ["id", "fecha_nota", "texto", "urgencia", "creado_en"],
            notas_enf,
        )

        for table in (
            "visitas",
            "revision_ocular",
            "pacientes",
            "checklist_items",
            "notas_esquemas",
            "notas_enfermeria",
        ):
            reset_sequence(pg_cur, table)

        pg_conn.commit()

        print("Migration completed successfully.")
        print(f"visitas: {len(visitas)}")
        print(f"revision_ocular: {len(revision)}")
        print(f"pacientes: {len(pacientes)}")
        print(f"checklist_items: {len(checklist)}")
        print(f"notas_esquemas: {len(notas_esquemas)}")
        print(f"notas_enfermeria: {len(notas_enf)}")
        return 0
    except Exception as exc:
        pg_conn.rollback()
        print(f"ERROR during migration: {exc}")
        return 1
    finally:
        sqlite_conn.close()
        pg_cur.close()
        pg_conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
