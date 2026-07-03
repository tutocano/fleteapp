# Ejemplo de JSON en lote (varias rutas en un archivo)

A diferencia de los CSV de ejemplo en `backend/ejemplos_csv/` (que usan codigos/nombres de
negocio y funcionan tal cual en cualquier ambiente), el formato JSON sigue usando **IDs
internos de base de datos** (`centro_distribucion_id`, `transportista_id`,
`tarifa_transportista_id`, `tipo_camion_id`, `cliente_id`, `producto_id`) -- el mismo formato
que ya usa la importacion JSON de una sola ruta (ver pantalla "Rutas" o el `README.md`
principal). Por eso estos 2 archivos son una **plantilla de estructura**, no un ejemplo listo
para subir sin cambios: los IDs (`1`, `2`, etc.) deben reemplazarse por los IDs reales de tu
empresa antes de usarlos (puedes verlos en las pantallas de Clientes, Productos, CEDIs,
Transportistas y Tarifas).

## Archivos

- `lote_planificadas_ejemplo.json`: arreglo con 2 rutas planificadas.
- `lote_ejecutadas_ejemplo.json`: las mismas 2 rutas, ya ejecutadas. Reemplaza
  `ruta_planificada_id: null` por el ID real que devolvio la importacion de cada planificada
  (se puede ver en la respuesta de la carga, o en la tabla "Rutas registradas" de la pantalla).

## Formato

Un arreglo (`[ ... ]`) donde cada elemento tiene exactamente el mismo formato que ya acepta
`POST /api/rutas/importar/planificada` (o `/ejecutada`) para una sola ruta. Tambien se acepta
un solo objeto (sin arreglo) por comodidad.

Si prefieres no lidiar con IDs internos, usa el formato **CSV** en su lugar (pestaña CSV de la
pantalla Rutas, o `backend/ejemplos_csv/`): identifica todo por codigo/nombre de negocio y
funciona igual sin importar el ambiente.
