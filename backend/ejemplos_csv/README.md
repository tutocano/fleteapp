# Ejemplos de CSV para importar rutas

Estos 4 archivos son ejemplos reales y listos para subir tal cual desde la
pantalla "Rutas" (pestaña CSV), usando los codigos/nombres que ya existen en
cada una de las 2 empresas cargadas de fabrica. Sirven como plantilla para que
cada empresa arme el CSV de su propia operacion diaria.

- `empresa1_planificada_ejemplo.csv` / `empresa1_ejecutada_ejemplo.csv`:
  para "Distribuidora ConsumoMasivo S.A.S." (empresa creada por `seed.py`).
- `empresa_demo2_planificada_ejemplo.csv` / `empresa_demo2_ejecutada_ejemplo.csv`:
  para "Empresa Demo 2" (creada por `migrate_v4_backfill.py` + `seed_empresa_demo_2.py`).

## Orden de carga

1. Sube primero el CSV de **planificada**.
2. Luego sube el CSV de **ejecutada** con los mismos valores de `codigo_ruta`
   (el sistema busca automaticamente la ruta planificada correspondiente; no
   hay que indicar ningun ID).

## Formato (ver `backend/app/services/csv_import.py` para el detalle completo)

Una fila = un pedido (producto + cantidad) dentro de una parada dentro de una
ruta. Varias filas con el mismo `codigo_ruta` arman la misma ruta; varias filas
con la misma `secuencia` arman la misma parada (con varios productos).

Columnas obligatorias: `codigo_ruta`, `centro_distribucion_codigo`,
`transportista_nombre`, `tarifa_nombre`, `tipo_camion_nombre`, `secuencia`,
`cliente_codigo`, `producto_codigo`, `cantidad`.

Columnas opcionales (se pueden dejar vacias): `fecha`, `flota_placa`,
`tiempo_servicio_min`, `distancia_km_tramo`, `tiempo_transito_min_tramo`,
`hora_llegada_estimada`, `hora_llegada_real`, `peso_kg`, `volumen_m3`.

Los datos se identifican por **codigo** de negocio (Centro de Distribucion,
Cliente, Producto) o por **nombre** (Transportista, Tipo de Camion, Tarifa de
Transportista) -- los mismos valores que ya se ven en sus respectivas
pantallas, nunca por ID interno de base de datos.
