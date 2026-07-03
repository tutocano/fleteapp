-- ============================================================
-- Migracion v4: usuarios, roles y empresa_id en catalogos.
--
-- Correr este script MANUALMENTE contra la base de datos de produccion
-- ANTES de desplegar el codigo nuevo (mismo patron que v3: create_all() de
-- SQLAlchemy solo crea tablas que no existen, nunca altera las existentes).
--
-- Es idempotente: usa IF NOT EXISTS / DO blocks, se puede correr varias veces
-- sin error. NO pone las columnas nuevas como NOT NULL todavia -- eso lo hace
-- migrate_v4_backfill.py DESPUES de rellenar los valores (ver ese script).
--
-- Uso (igual que las migraciones anteriores, con psql apuntando a la
-- External Database URL de Render):
--   psql "<external DATABASE_URL>/flete_db" -f migrate_v4_alter.sql
-- ============================================================

-- ---------- Tabla usuario (nueva) ----------
CREATE TABLE IF NOT EXISTS usuario (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(200) NOT NULL,
    email VARCHAR(200) NOT NULL UNIQUE,
    password_hash VARCHAR(200) NOT NULL,
    rol VARCHAR(30) NOT NULL,
    empresa_id INTEGER REFERENCES empresa(id) ON DELETE CASCADE,
    activo BOOLEAN NOT NULL DEFAULT true,
    creado_en TIMESTAMP NOT NULL DEFAULT now()
);

-- ---------- empresa_id nuevo en catalogos (nullable por ahora) ----------
ALTER TABLE tipo_cliente ADD COLUMN IF NOT EXISTS empresa_id INTEGER REFERENCES empresa(id) ON DELETE CASCADE;
ALTER TABLE zona_geografica ADD COLUMN IF NOT EXISTS empresa_id INTEGER REFERENCES empresa(id) ON DELETE CASCADE;
ALTER TABLE tipo_camion ADD COLUMN IF NOT EXISTS empresa_id INTEGER REFERENCES empresa(id) ON DELETE CASCADE;
ALTER TABLE producto ADD COLUMN IF NOT EXISTS empresa_id INTEGER REFERENCES empresa(id) ON DELETE CASCADE;
ALTER TABLE metodo_tarifa ADD COLUMN IF NOT EXISTS empresa_id INTEGER REFERENCES empresa(id) ON DELETE CASCADE;

-- ---------- empresa_id "por consistencia" (v4) ----------
ALTER TABLE flota ADD COLUMN IF NOT EXISTS empresa_id INTEGER REFERENCES empresa(id) ON DELETE CASCADE;
ALTER TABLE tarifa_transportista ADD COLUMN IF NOT EXISTS empresa_id INTEGER REFERENCES empresa(id) ON DELETE CASCADE;
ALTER TABLE ruta ADD COLUMN IF NOT EXISTS empresa_id INTEGER REFERENCES empresa(id) ON DELETE CASCADE;

-- ---------- Quitar las restricciones UNIQUE globales que ahora deben ser
-- compuestas (empresa_id, codigo)/(empresa_id, nombre). Los nombres de
-- constraint por defecto de Postgres siguen el patron <tabla>_<columna>_key;
-- se protegen con IF EXISTS por si el nombre real difiere. -----------------
ALTER TABLE tipo_cliente DROP CONSTRAINT IF EXISTS tipo_cliente_nombre_key;
ALTER TABLE producto DROP CONSTRAINT IF EXISTS producto_codigo_key;
ALTER TABLE metodo_tarifa DROP CONSTRAINT IF EXISTS metodo_tarifa_codigo_key;
ALTER TABLE centro_distribucion DROP CONSTRAINT IF EXISTS centro_distribucion_codigo_key;
ALTER TABLE cliente DROP CONSTRAINT IF EXISTS cliente_codigo_key;

-- (Los indices/constraints compuestos nuevos, y el NOT NULL de las columnas
-- empresa_id de arriba, se agregan desde migrate_v4_backfill.py DESPUES de
-- rellenar los valores -- no se puede poner NOT NULL/UNIQUE antes de tener
-- datos consistentes.)
