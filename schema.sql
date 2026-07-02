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

CREATE TABLE IF NOT EXISTS centro_distribucion (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER NOT NULL REFERENCES empresa(id) ON DELETE CASCADE,
    nombre VARCHAR(200) NOT NULL,
    codigo VARCHAR(50) UNIQUE,
    latitud DOUBLE PRECISION NOT NULL,
    longitud DOUBLE PRECISION NOT NULL,
    direccion VARCHAR(300),
    creado_en TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS tipo_cliente (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE,
    descripcion VARCHAR(300)
);

CREATE TABLE IF NOT EXISTS zona_geografica (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(150) NOT NULL,
    descripcion VARCHAR(300),
    tarifa_zona DOUBLE PRECISION NOT NULL DEFAULT 0,
    creado_en TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cliente (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER NOT NULL REFERENCES empresa(id) ON DELETE CASCADE,
    tipo_cliente_id INTEGER REFERENCES tipo_cliente(id),
    zona_geografica_id INTEGER REFERENCES zona_geografica(id),
    nombre VARCHAR(200) NOT NULL,
    codigo VARCHAR(50) UNIQUE,
    latitud DOUBLE PRECISION NOT NULL,
    longitud DOUBLE PRECISION NOT NULL,
    direccion VARCHAR(300),
    canal VARCHAR(100),
    creado_en TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS tipo_camion (
    id SERIAL PRIMARY KEY,
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

CREATE TABLE IF NOT EXISTS flota (
    id SERIAL PRIMARY KEY,
    transportista_id INTEGER NOT NULL REFERENCES transportista(id) ON DELETE CASCADE,
    tipo_camion_id INTEGER NOT NULL REFERENCES tipo_camion(id),
    placa VARCHAR(20),
    descripcion VARCHAR(200),
    activo BOOLEAN NOT NULL DEFAULT true
);

CREATE TABLE IF NOT EXISTS metodo_tarifa (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(50) NOT NULL UNIQUE,
    nombre VARCHAR(150) NOT NULL,
    descripcion VARCHAR(400)
);

CREATE TABLE IF NOT EXISTS tarifa_transportista (
    id SERIAL PRIMARY KEY,
    transportista_id INTEGER NOT NULL REFERENCES transportista(id) ON DELETE CASCADE,
    metodo_tarifa_id INTEGER NOT NULL REFERENCES metodo_tarifa(id),
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

CREATE TABLE IF NOT EXISTS producto (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(200) NOT NULL,
    codigo VARCHAR(50) UNIQUE,
    peso_unitario_kg DOUBLE PRECISION NOT NULL,
    volumen_unitario_m3 DOUBLE PRECISION NOT NULL
);

CREATE TABLE IF NOT EXISTS ruta (
    id SERIAL PRIMARY KEY,
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

CREATE TABLE IF NOT EXISTS parada_ruta (
    id SERIAL PRIMARY KEY,
    ruta_id INTEGER NOT NULL REFERENCES ruta(id) ON DELETE CASCADE,
    cliente_id INTEGER NOT NULL REFERENCES cliente(id),
    secuencia INTEGER NOT NULL,
    distancia_km_tramo DOUBLE PRECISION NOT NULL DEFAULT 0,
    tiempo_transito_min_tramo DOUBLE PRECISION NOT NULL DEFAULT 0,
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

-- Metodos de tarifa fijos (seed minimo de catalogo)
INSERT INTO metodo_tarifa (codigo, nombre, descripcion) VALUES
    ('POR_VIAJE', 'Por viaje', 'Tarifa fija por viaje completo, sin importar paradas ni distancia'),
    ('POR_PARADA', 'Por numero de paradas', 'Tarifa por cada parada (cliente) visitada en la ruta'),
    ('POR_ZONA', 'Por zona de entrega', 'Tarifa de la zona mas alejada/costosa entre los clientes de la ruta'),
    ('POR_PESO_VOLUMEN', 'Por volumen o peso entregado', 'Tarifa por m3 o por kg entregado, sumando todos los clientes de la ruta'),
    ('POR_TIEMPO_SERVICIO', 'Por tiempo de servicio', 'Tarifa por hora/minuto de atencion en clientes, sumada en la ruta')
ON CONFLICT (codigo) DO NOTHING;
