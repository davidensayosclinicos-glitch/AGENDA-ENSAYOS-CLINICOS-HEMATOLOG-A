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

-- Índices únicos para asegurar el funcionamiento de ON CONFLICT en tablas preexistentes
CREATE UNIQUE INDEX IF NOT EXISTS idx_inventario_kits_codigo_barras ON inventario_kits (codigo_barras);
CREATE UNIQUE INDEX IF NOT EXISTS idx_catalogo_tipos_ensayo_tipo ON catalogo_tipos_por_ensayo (ensayo, tipo_de_kit);
CREATE UNIQUE INDEX IF NOT EXISTS idx_ensayos_configurados_ensayo ON ensayos_configurados (ensayo);
