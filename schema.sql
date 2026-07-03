-- ============================================================
-- Sistema de Gestion y Conciliacion de Costos de Flete
-- DDL PostgreSQL
-- ============================================================

CREATE TABLE IF NOT EXISTS empresa (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(200) NOT NULL,
    nit VARCHAR(50),
    direccion VARCHAR(300),
    telefono VARCHAR(50),
    email VARCHAR(150),
    creado_en TIMESTAMP NOT NULL DEFAULT now()
);

-- v4: usuarios, roles y multi-empresa. Un usuario tiene exactamente un rol y
-- pertenece a una sola empresa (excepto SUPER_ADMIN, que no pertenece a
-- ninguna en particular porque opera sobre todas). Ver PLAN_V4_USUARIOS_ROLES.md.
CREATE TABLE IF NOT EXISTS usuario (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(200) NOT NULL,
    email VARCHAR(200) NOT NULL UNIQUE,
    password_hash VARCHAR(200) NOT NULL,
    rol VARCHAR(30) NOT NULL, -- SUPER_ADMIN | EMPRESA_ADMIN | INTERFAZ | USUARIO_FINAL
    empresa_id INTEGER REFERENCES empresa(id) ON DELETE CASCADE, -- NULL solo para SUPER_ADMIN
    activo BOOLEAN NOT NULL DEFAULT true,
    creado_en TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS centro_distribucion (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER NOT NULL REFERENCES empresa(id) ON DELETE CASCADE,
    nombre VARCHAR(200) NOT NULL,
    codigo VARCHAR(50),
    latitud DOUBLE PRECISION NOT NULL,
    longitud DOUBLE PRECISION NOT NULL,
    direccion VARCHAR(300),
    creado_en TIMESTAMP NOT NULL DEFAULT now(),
    UNIQUE(empresa_id, codigo)
);

-- v4: TipoCliente pasa de catalogo global a catalogo por empresa.
CREATE TABLE IF NOT EXISTS tipo_cliente (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER NOT NULL REFERENCES empresa(id) ON DELETE CASCADE,
    nombre VARCHAR(100) NOT NULL,
    descripcion VARCHAR(300),
    UNIQUE(empresa_id, nombre)
);

-- v4: ZonaGeografica pasa de catalogo global a catalogo por empresa.
CREATE TABLE IF NOT EXISTS zona_geografica (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER NOT NULL REFERENCES empresa(id) ON DELETE CASCADE,
    nombre VARCHAR(150) NOT NULL,
    descripcion VARCHAR(300),
    tarifa_zona DOUBLE PRECISION NOT NULL DEFAULT 0,
    -- v2: poligono aproximado [[lat,lon], ...] construido manualmente (no oficial),
    -- usado para determinar automaticamente la zona de un punto por punto-en-poligono.
    -- Reemplazable en el futuro por un GeoJSON oficial de IDECA sin cambiar el esquema.
    poligono JSONB,
    creado_en TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cliente (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER NOT NULL REFERENCES empresa(id) ON DELETE CASCADE,
    tipo_cliente_id INTEGER REFERENCES tipo_cliente(id),
    zona_geografica_id INTEGER REFERENCES zona_geografica(id),
    nombre VARCHAR(200) NOT NULL,
    codigo VARCHAR(50),
    latitud DOUBLE PRECISION NOT NULL,
    longitud DOUBLE PRECISION NOT NULL,
    direccion VARCHAR(300),
    canal VARCHAR(100),
    creado_en TIMESTAMP NOT NULL DEFAULT now(),
    UNIQUE(empresa_id, codigo)
);

-- v4: TipoCamion pasa de catalogo global a catalogo por empresa.
CREATE TABLE IF NOT EXISTS tipo_camion (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER NOT NULL REFERENCES empresa(id) ON DELETE CASCADE,
    nombre VARCHAR(100) NOT NULL,
    capacidad_peso_kg DOUBLE PRECISION NOT NULL,
    capacidad_volumen_m3 DOUBLE PRECISION NOT NULL
);

CREATE TABLE IF NOT EXISTS transportista (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER NOT NULL REFERENCES empresa(id) ON DELETE CASCADE,
    nombre VARCHAR(200) NOT NULL,
    nit VARCHAR(50),
    contacto VARCHAR(150),
    telefono VARCHAR(50),
    creado_en TIMESTAMP NOT NULL DEFAULT now()
);

-- v3: relacion informativa (no bloquea import de rutas) de que zonas atiende
-- cada transportista. No tiene empresa_id propio: se valida a traves de
-- transportista_id/zona_geografica_id, que ya son de la misma empresa.
CREATE TABLE IF NOT EXISTS transportista_zona_cobertura (
    id SERIAL PRIMARY KEY,
    transportista_id INTEGER NOT NULL REFERENCES transportista(id) ON DELETE CASCADE,
    zona_geografica_id INTEGER NOT NULL REFERENCES zona_geografica(id) ON DELETE CASCADE,
    UNIQUE(transportista_id, zona_geografica_id)
);

-- v4: empresa_id agregado por consistencia (ya era derivable via transportista_id).
CREATE TABLE IF NOT EXISTS flota (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER NOT NULL REFERENCES empresa(id) ON DELETE CASCADE,
    transportista_id INTEGER NOT NULL REFERENCES transportista(id) ON DELETE CASCADE,
    tipo_camion_id INTEGER NOT NULL REFERENCES tipo_camion(id),
    placa VARCHAR(20),
    descripcion VARCHAR(200),
    activo BOOLEAN NOT NULL DEFAULT true
);

-- v4: MetodoTarifa pasa de catalogo global a catalogo por empresa (se clonan
-- los 6 metodos fijos automaticamente cada vez que se crea una empresa nueva).
CREATE TABLE IF NOT EXISTS metodo_tarifa (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER NOT NULL REFERENCES empresa(id) ON DELETE CASCADE,
    codigo VARCHAR(50) NOT NULL,
    nombre VARCHAR(150) NOT NULL,
    descripcion VARCHAR(400),
    UNIQUE(empresa_id, codigo)
);

-- v4: empresa_id agregado por consistencia (ya era derivable via transportista_id).
CREATE TABLE IF NOT EXISTS tarifa_transportista (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER NOT NULL REFERENCES empresa(id) ON DELETE CASCADE,
    transportista_id INTEGER NOT NULL REFERENCES transportista(id) ON DELETE CASCADE,
    metodo_tarifa_id INTEGER NOT NULL REFERENCES metodo_tarifa(id),
    -- NULL = la tarifa aplica a cualquier tipo de camion (retrocompatible con v1/v2).
    -- Si se especifica, esta tarifa solo aplica para ese tipo de camion puntual.
    tipo_camion_id INTEGER REFERENCES tipo_camion(id),
    nombre VARCHAR(150) NOT NULL,
    valor_unitario DOUBLE PRECISION NOT NULL DEFAULT 0,
    unidad VARCHAR(30),
    activo BOOLEAN NOT NULL DEFAULT true,
    creado_en TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS tarifa_zona_detalle (
    id SERIAL PRIMARY KEY,
    tarifa_transportista_id INTEGER NOT NULL REFERENCES tarifa_transportista(id) ON DELETE CASCADE,
    zona_geografica_id INTEGER NOT NULL REFERENCES zona_geografica(id),
    valor DOUBLE PRECISION NOT NULL DEFAULT 0,
    UNIQUE(tarifa_transportista_id, zona_geografica_id)
);

-- v4: Producto pasa de catalogo global a catalogo por empresa.
CREATE TABLE IF NOT EXISTS producto (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER NOT NULL REFERENCES empresa(id) ON DELETE CASCADE,
    nombre VARCHAR(200) NOT NULL,
    codigo VARCHAR(50),
    peso_unitario_kg DOUBLE PRECISION NOT NULL,
    volumen_unitario_m3 DOUBLE PRECISION NOT NULL,
    UNIQUE(empresa_id, codigo)
);

-- v4: empresa_id agregado por consistencia (ya era derivable via centro_distribucion_id).
CREATE TABLE IF NOT EXISTS ruta (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER NOT NULL REFERENCES empresa(id) ON DELETE CASCADE,
    codigo_ruta VARCHAR(50) NOT NULL,
    es_planificada BOOLEAN NOT NULL DEFAULT true,
    ruta_planificada_id INTEGER REFERENCES ruta(id) ON DELETE SET NULL,
    centro_distribucion_id INTEGER NOT NULL REFERENCES centro_distribucion(id),
    transportista_id INTEGER NOT NULL REFERENCES transportista(id),
    tarifa_transportista_id INTEGER NOT NULL REFERENCES tarifa_transportista(id),
    tipo_camion_id INTEGER NOT NULL REFERENCES tipo_camion(id),
    flota_id INTEGER REFERENCES flota(id),
    fecha TIMESTAMP NOT NULL DEFAULT now(),
    estado VARCHAR(30) NOT NULL DEFAULT 'REGISTRADA',
    costo_flete_calculado DOUBLE PRECISION,
    detalle_calculo JSONB,
    creado_en TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ruta_planificada_id ON ruta(ruta_planificada_id);
CREATE INDEX IF NOT EXISTS idx_ruta_transportista ON ruta(transportista_id);
CREATE INDEX IF NOT EXISTS idx_ruta_empresa ON ruta(empresa_id);

CREATE TABLE IF NOT EXISTS parada_ruta (
    id SERIAL PRIMARY KEY,
    ruta_id INTEGER NOT NULL REFERENCES ruta(id) ON DELETE CASCADE,
    cliente_id INTEGER NOT NULL REFERENCES cliente(id),
    secuencia INTEGER NOT NULL,
    distancia_km_tramo DOUBLE PRECISION NOT NULL DEFAULT 0,
    tiempo_transito_min_tramo DOUBLE PRECISION NOT NULL DEFAULT 0,
    -- v3: distancia/tiempo de referencia (Google/Haversine), no pisan lo importado.
    distancia_km_tramo_referencia DOUBLE PRECISION,
    tiempo_transito_min_tramo_referencia DOUBLE PRECISION,
    fuente_referencia VARCHAR(30),
    tiempo_servicio_min DOUBLE PRECISION NOT NULL DEFAULT 0,
    hora_llegada_estimada TIMESTAMP,
    hora_llegada_real TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_parada_ruta_ruta_id ON parada_ruta(ruta_id);

CREATE TABLE IF NOT EXISTS pedido_cliente_ruta (
    id SERIAL PRIMARY KEY,
    parada_ruta_id INTEGER NOT NULL REFERENCES parada_ruta(id) ON DELETE CASCADE,
    producto_id INTEGER NOT NULL REFERENCES producto(id),
    cantidad DOUBLE PRECISION NOT NULL DEFAULT 0,
    peso_kg DOUBLE PRECISION NOT NULL DEFAULT 0,
    volumen_m3 DOUBLE PRECISION NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_pedido_parada_ruta_id ON pedido_cliente_ruta(parada_ruta_id);

-- Nota v4: los metodos de tarifa YA NO se siembran aqui de forma global -- se
-- clonan automaticamente (6 metodos fijos) cada vez que se crea una empresa
-- nueva via POST /api/empresas (ver app/routers/maestros.py,
-- sembrar_metodos_tarifa_para_empresa).
