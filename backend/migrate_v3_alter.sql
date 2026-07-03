-- ============================================================
-- Migracion v3 (retroactiva): cobertura de zonas por transportista +
-- distancia/tiempo de referencia por parada.
--
-- Esta migracion se aplico en su momento contra produccion (Render) de forma
-- manual, sin dejar un script guardado en el repo. Si tienes un ambiente
-- (por ejemplo tu Postgres local de docker compose) que viene de antes de v3
-- y nunca recibio estos cambios, correr este script ANTES de
-- migrate_v4_alter.sql (v4 asume que estas tablas/columnas ya existen).
--
-- Es idempotente: usa IF NOT EXISTS, se puede correr varias veces sin error.
--
-- Uso:
--   docker compose exec -T postgres psql -U flete_user -d flete_db < backend/migrate_v3_alter.sql
-- ============================================================

CREATE TABLE IF NOT EXISTS transportista_zona_cobertura (
    id SERIAL PRIMARY KEY,
    transportista_id INTEGER NOT NULL REFERENCES transportista(id) ON DELETE CASCADE,
    zona_geografica_id INTEGER NOT NULL REFERENCES zona_geografica(id) ON DELETE CASCADE,
    UNIQUE(transportista_id, zona_geografica_id)
);

ALTER TABLE parada_ruta ADD COLUMN IF NOT EXISTS distancia_km_tramo_referencia DOUBLE PRECISION;
ALTER TABLE parada_ruta ADD COLUMN IF NOT EXISTS tiempo_transito_min_tramo_referencia DOUBLE PRECISION;
ALTER TABLE parada_ruta ADD COLUMN IF NOT EXISTS fuente_referencia VARCHAR(30);
