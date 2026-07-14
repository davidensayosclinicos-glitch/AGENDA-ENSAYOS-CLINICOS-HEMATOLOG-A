-- Tablas necesarias para el inventario de kits en Supabase/PostgreSQL.
-- Ejecuta este script en el SQL Editor del mismo proyecto donde ya tienes
-- las tablas del ensayo.

CREATE TABLE IF NOT EXISTS inventario_kits (
    id BIGSERIAL PRIMARY KEY,
    codigo_barras TEXT NOT NULL UNIQUE,
    ensayo TEXT NOT NULL,
    tipo_de_kit TEXT NOT NULL,
    caducidad TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS historial_kits (
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
);

CREATE TABLE IF NOT EXISTS catalogo_tipos_por_ensayo (
    id BIGSERIAL PRIMARY KEY,
    ensayo TEXT NOT NULL,
    tipo_de_kit TEXT NOT NULL,
    UNIQUE (ensayo, tipo_de_kit)
);

CREATE TABLE IF NOT EXISTS ensayos_configurados (
    id BIGSERIAL PRIMARY KEY,
    ensayo TEXT NOT NULL UNIQUE
);
