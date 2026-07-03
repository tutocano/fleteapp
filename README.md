# Fleteapp — Sistema de Gestion y Conciliacion de Costos de Flete

Prototipo funcional completo para gestionar y conciliar costos de flete de una empresa
distribuidora/manufacturera de consumo masivo, cubriendo los 5 metodos de tarifa mas
comunes en la industria (por viaje, por parada, por zona, por peso/volumen, por tiempo
de servicio) y comparando el costo planificado vs. el costo real ejecutado.

## Stack

- **Backend**: Python 3.11, FastAPI, SQLAlchemy 2.0, PostgreSQL 15.
- **Frontend**: React 18 + Vite, Leaflet / react-leaflet (mapas OpenStreetMap, sin API key).
- **Orquestacion**: Docker Compose (postgres + backend + frontend).

## Estructura del proyecto

```
fleteapp/
  MODELO_DATOS.md              # ERD (mermaid) + descripcion de tablas
  schema.sql                   # DDL PostgreSQL completo
  docker-compose.yml
  README.md
  ARQUITECTURA_Y_DESPLIEGUE.md
  backend/
    app/
      main.py                  # FastAPI app, monta routers, siembra catalogo de metodos
      database.py               # engine/session SQLAlchemy
      models/models.py          # modelos ORM de todas las entidades
      schemas/schemas.py         # esquemas Pydantic (request/response)
      routers/
        maestros.py             # CRUD de empresa, cedis, clientes, transportistas, tarifas, etc.
        rutas.py                # import de rutas planificadas/ejecutadas + calculo + mapa
        conciliacion.py          # endpoints de conciliacion por ruta y por transportista
      services/
        flete_calculo.py         # logica de los 5 metodos de tarifa
        distance_connector.py    # conector pluggable Haversine / Google Routes API
    seed.py                    # script de datos semilla (usa la API HTTP)
    requirements.txt
    Dockerfile
  frontend/
    src/
      pages/                   # paginas de maestros, rutas, mapa, conciliacion
      components/CrudTable.jsx # componente generico de tabla CRUD
      api/client.js            # cliente axios
    package.json
    Dockerfile
    vite.config.js
```

## Como correr el sistema completo

### Requisitos
- Docker y Docker Compose instalados.

### Pasos

```bash
cd fleteapp
docker-compose up -d --build
```

Esto levanta:
- **postgres** en el puerto `5432` (usuario `flete_user`, password `flete_pass`, db `flete_db`)
- **backend** (FastAPI) en `http://localhost:8000` — documentacion interactiva en `http://localhost:8000/docs`
- **frontend** (React/Vite) en `http://localhost:5173`

Espera unos segundos a que los 3 contenedores esten sanos:

```bash
docker-compose ps
```

### Cargar datos de ejemplo (seed)

Con el backend ya corriendo:

```bash
docker-compose exec backend python seed.py
```

Esto crea: 1 empresa, 2 CEDIs, 15 clientes en Bogota, 3 tipos de camion, 3 transportistas
(con tarifas que cubren los 5 metodos), 4 zonas geograficas, 8 productos, y 5 rutas
planificadas + sus correspondientes rutas ejecutadas (con diferencias deliberadas) para
poder ver la conciliacion con datos reales.

### Explorar

- Abre `http://localhost:5173` para el frontend.
- Ve a **Conciliacion** para ver las diferencias planificado vs. real.
- Ve a **Mapa de Rutas**, selecciona una ruta y observa la polilinea planificada (azul) vs. ejecutada (verde punteada).
- Ve a **Rutas (Import)** para subir un JSON de ejemplo de una nueva ruta.
- La documentacion interactiva de la API (Swagger) esta en `http://localhost:8000/docs`.

### Apagar

```bash
docker-compose down
```

Para borrar tambien el volumen de datos de Postgres:

```bash
docker-compose down -v
```

## Variables de entorno relevantes

| Variable | Donde | Descripcion |
|---|---|---|
| `DATABASE_URL` | backend | Cadena de conexion SQLAlchemy a PostgreSQL |
| `GOOGLE_MAPS_API_KEY` | backend | Si se define, el conector de distancia/tiempo intenta usar Google Routes API antes de caer a Haversine. Si no se define (o falla la llamada), se usa Haversine automaticamente. |
| `VITE_API_URL` | frontend | URL base de la API consumida por el frontend |

## Los 5 metodos de tarifa (resumen)

1. **POR_VIAJE**: tarifa fija, sin importar numero de paradas ni distancia.
2. **POR_PARADA**: tarifa unitaria x numero de clientes visitados en la ruta.
3. **POR_ZONA**: cada cliente cae en una zona geografica con tarifa propia (por transportista); se toma la tarifa de la zona MAS COSTOSA entre todos los clientes de la ruta y se aplica al viaje completo (no se suman las zonas).
4. **POR_PESO_VOLUMEN**: tarifa unitaria x kg o m3 totales entregados en la ruta (segun configuracion de unidad).
5. **POR_TIEMPO_SERVICIO**: tarifa unitaria x minutos u horas totales de atencion en los clientes de la ruta.

## Importacion de rutas (formato JSON)

Ejemplo de payload para `POST /api/rutas/importar/planificada`:

```json
{
  "codigo_ruta": "RUTA-DEMO-001",
  "centro_distribucion_id": 1,
  "transportista_id": 2,
  "tarifa_transportista_id": 3,
  "tipo_camion_id": 3,
  "fecha": "2026-07-01T07:00:00",
  "paradas": [
    {
      "cliente_id": 1,
      "secuencia": 1,
      "tiempo_servicio_min": 20,
      "pedidos": [{ "producto_id": 1, "cantidad": 50 }]
    }
  ]
}
```

Si `distancia_km_tramo` / `tiempo_transito_min_tramo` no se incluyen, el backend los calcula
automaticamente usando el conector pluggable (Haversine por defecto).

Para importar la ruta EJECUTADA correspondiente, usa `POST /api/rutas/importar/ejecutada` con
el mismo formato, agregando `"ruta_planificada_id": <id de la ruta planificada>`.

### Varias rutas en un solo archivo JSON

`POST /api/rutas/importar-json-lote/planificada` y `.../ejecutada` (multipart, campo `archivo`)
aceptan un unico archivo `.json` con un **arreglo** de rutas (cada una en el mismo formato de
arriba) para cargar de un tiron todas las rutas de un dia. Sigue usando IDs internos (a
diferencia del CSV); ver `backend/ejemplos_json/` para una plantilla.

## Importacion de rutas (formato CSV, v4.1)

Alternativa al JSON de arriba para cargar de un tiron TODAS las rutas de un dia completo
de operacion (varias rutas, cada una con varias paradas y varios productos), identificando
cada entidad por su codigo/nombre de negocio en vez de por ID interno. Disponible en la misma
pantalla "Rutas" (pestaña "CSV"), o directo contra `POST /api/rutas/importar-csv/planificada`
y `POST /api/rutas/importar-csv/ejecutada` (multipart, campo `archivo`).

Una fila del CSV = un pedido dentro de una parada dentro de una ruta. Columnas obligatorias:
`codigo_ruta, centro_distribucion_codigo, transportista_nombre, tarifa_nombre,
tipo_camion_nombre, secuencia, cliente_codigo, producto_codigo, cantidad`. Columnas opcionales:
`fecha, flota_placa, tiempo_servicio_min, distancia_km_tramo, tiempo_transito_min_tramo,
hora_llegada_estimada, hora_llegada_real, peso_kg, volumen_m3`.

Para el CSV de ejecutada no se indica ningun ID: el `codigo_ruta` debe coincidir con el de una
ruta planificada ya importada en la misma empresa (se busca automaticamente). Ver
`backend/app/services/csv_import.py` para el detalle de la logica, y
`backend/ejemplos_csv/` para 4 archivos de ejemplo reales (uno planificada + uno ejecutada, para
cada una de las 2 empresas cargadas de fabrica) listos para subir tal cual.

## Limitaciones conocidas del prototipo

- No usa PostGIS; lat/lon se guardan como floats simples (suficiente para prototipo, sin
  necesidad de consultas espaciales avanzadas).
- El conector de Google Routes API es un stub funcional (implementado y listo para usar),
  pero no fue probado contra la API real de Google dentro de este ejercicio (requiere una
  API key valida y facturacion activa en GCP).
- No hay autenticacion/autorizacion (fuera de alcance para un prototipo funcional).
- El formulario de tarifas en el frontend es funcional pero minimalista (sin validaciones
  avanzadas de negocio como duplicados).
- La secuencia de paradas se asume ya optimizada al momento de importar (el sistema no
  hace ruteo/optimizacion, solo calcula costos sobre la secuencia dada).

## Novedades v2

Version 2 agrega 5 capacidades sobre el prototipo original (v1, protegido con tag `v1.0`
en git), sin romper compatibilidad con las rutas y calculos existentes.

1. **Poligonos de zona geografica.** `ZonaGeografica` tiene un nuevo campo JSON `poligono`
   (lista de vertices `[lat, lon]`) que delimita cada una de las 4 zonas del seed (Centro,
   Norte, Sur, Occidente/Soacha) sobre el mapa de Bogota. **Importante:** estos poligonos
   fueron construidos manualmente por el equipo de desarrollo a partir del conocimiento
   general de la geografia/localidades de Bogota (8-12 vertices cada uno) porque el intento
   de descargar el GeoJSON oficial de localidades desde IDECA fue bloqueado por el entorno
   de desarrollo. **No son un shapefile oficial** — son una aproximacion razonable para un
   prototipo, verificada para que los clientes y CEDIs del seed caigan dentro de alguna zona
   y que los 4 poligonos no se solapen entre si. El modelo de datos esta preparado para que
   en el futuro se reemplace este campo con el GeoJSON real de IDECA (https://www.ideca.gov.co/)
   sin cambiar el esquema: basta con sobreescribir `poligono` con las coordenadas oficiales.

2. **Metodo de tarifa POR_KILOMETRO.** Nuevo metodo en el catalogo (`backend/app/main.py`):
   costo = `valor_unitario` (precio por km) x distancia total de la ruta (suma de
   `distancia_km_tramo` de todas sus paradas). Aplica igual a rutas planificadas y ejecutadas,
   cada una con sus propias distancias, lo que permite ver diferencias reales en la conciliacion
   cuando el recorrido real es mas largo que el planificado. Ver `RUTA-BOG-008` en el seed.

3. **Deteccion automatica de zona por punto-en-poligono.** El metodo POR_ZONA ya no depende
   unicamente del `zona_geografica_id` fijo del cliente: para cada parada de la ruta se
   calcula la zona real segun las coordenadas del cliente y los poligonos (algoritmo de
   ray casting en Python puro, `backend/app/services/geo.py`, sin dependencias nuevas). Si el
   punto no cae en ningun poligono, se usa como respaldo el `zona_geografica_id` manual del
   cliente (caso borde), y el detalle de calculo deja registrado explicitamente si se uso ese
   respaldo (`uso_respaldo_manual`) para cada parada.

4. **Mapa general de clientes y CEDIs** (`/mapa-general` en el frontend). Muestra en un solo
   mapa todos los clientes (con canal/tipo en el popup) y todos los centros de distribucion,
   sin necesidad de seleccionar una ruta especifica, con los poligonos de zona como capa de
   fondo semi-transparente (un color distinto por zona).

5. **Detalle estructurado del calculo de flete.** En `Rutas (Import)` y `Conciliacion`, cada
   ruta tiene un boton "Ver calculo" que despliega una tabla con el metodo de tarifa aplicado,
   el valor unitario (ej. "$2,500/km", "$800/kg"), la base de calculo (ej. "14.5 km", "1,230 kg")
   y el costo total — ademas del texto de explicacion que ya existia. Para POR_ZONA se muestra
   tambien el detalle por parada (zona detectada por poligono, zona aplicada, si se uso respaldo
   manual).

6. **Tarifas diferenciadas por tipo de camion.** `TarifaTransportista` tiene un nuevo campo
   opcional `tipo_camion_id`. Si se deja vacio ("Cualquier camion" en el formulario de
   `Tarifas de Flete`), la tarifa aplica sin importar el camion usado en la ruta (comportamiento
   v1/v2, retrocompatible). Si se especifica, esa tarifa SOLO puede usarse en rutas con ese tipo
   de camion exacto — asi un mismo transportista puede cobrar distinto por el mismo metodo segun
   si usa un NHR, un Turbo o un Sencillo (ej. `RUTA-BOG-009` en el seed: POR_VIAJE con TransRapido
   cuesta $180,000 con tarifa restringida a NHR, contra $250,000 con la tarifa general). Al
   importar una ruta, si la tarifa elegida esta restringida a un camion distinto al de la ruta,
   la importacion se rechaza con un error explicativo (ver `backend/app/routers/rutas.py`). Esta
   misma columna generaliza la variable "tipo de camion" a los 6 metodos de tarifa sin tocar la
   logica de calculo de ninguno, porque el calculo siempre usa el `valor_unitario`/`zonas_detalle`
   de la fila de tarifa ya seleccionada.

## Novedades v3

Version 3 agrega 4 capacidades sobre v2 (protegido con tag `v2.0` en git), sin cambiar
el comportamiento de rutas/calculos/conciliacion existentes. Probado localmente (smoke
test de backend + build de frontend + seed completo) antes de publicar.

1. **Dibujo interactivo de poligonos de zona.** La pagina `Zonas Geograficas` ya no usa
   el formulario generico: incluye un mapa donde se dibuja el poligono a mano (editor
   propio, sin libreria externa -- se descarto `leaflet-draw` por bugs no resueltos con
   Leaflet 1.9.x/React 18). Click agrega un vertice, arrastrar lo mueve, click derecho lo
   borra; no tiene que coincidir con ninguna division administrativa oficial. El campo
   `poligono` sigue siendo el mismo JSON `[[lat,lon], ...]` de v2, asi que el
   punto-en-poligono de POR_ZONA sigue funcionando igual.

2. **Cobertura de zonas por transportista.** Nueva tabla `transportista_zona_cobertura`
   (muchos a muchos) y pantalla `Cobertura de Zonas` con una matriz de checkboxes
   (transportista x zona) para marcar que zonas atiende cada transportista. Es
   **informativa** (decision explicita del usuario): no bloquea el import de rutas, sirve
   como referencia para decidir que transportista asignar a una ruta.

3. **Tarifas por combinacion de zona y tipo de camion, editable en matriz.** No requirio
   cambios de esquema: `TarifaTransportista.tipo_camion_id` (v2) y `TarifaZonaDetalle`
   (v2) ya eran independientes entre si, asi que una tarifa POR_ZONA restringida a un
   tipo de camion ya tenia su propia tabla de valores por zona. La pagina `Tarifas de
   Flete` muestra una matriz (zona x tipo de camion) por transportista, editable celda a
   celda: crea o actualiza automaticamente la `TarifaTransportista` correspondiente al
   guardar.

4. **Distancia/tiempo de referencia (Google/Haversine) como dato adicional, no
   sustituto.** Cada parada de ruta (planificada y ejecutada) ahora guarda, ademas de la
   distancia/tiempo que venga en el JSON de importacion, una distancia/tiempo de
   **referencia** calculada siempre por el conector (`distance_connector.py`: Google
   Routes API si hay `GOOGLE_MAPS_API_KEY`, si no Haversine). El valor importado nunca se
   sobreescribe. El detalle de calculo de cada ruta (`Rutas` y `Conciliacion`) muestra
   ahora ambos valores lado a lado, la diferencia, y para el metodo POR_KILOMETRO
   ademas el costo resultante con cada uno -- asi se puede detectar si una ruta se
   planifico o ejecuto con datos de distancia/tiempo poco realistas.

## Novedades v4

Version 4 agrega autenticacion, 4 roles de usuario y aislamiento de datos por empresa
(multi-tenant: una sola instancia, una sola base de datos, todas las empresas conviven
ahi). Ver `PLAN_V4_USUARIOS_ROLES.md` para el diseno completo. Probado localmente
(smoke test de backend con TestClient, servidor real + curl, build de frontend) antes
de publicar.

1. **Usuarios y roles.** Nueva tabla `usuario` (login por correo+contrasena, hash con
   bcrypt, JWT sin refresh token, expira a las 12 horas). 4 roles fijos: `SUPER_ADMIN`
   (crea empresas y usuarios, ve/edita cualquier empresa), `EMPRESA_ADMIN` (CRUD completo
   de maestros dentro de su empresa), `INTERFAZ` (importa rutas planificadas/ejecutadas),
   `USUARIO_FINAL` (solo lectura: Mapa de Rutas, Mapa General, Conciliacion). Un usuario
   pertenece a una sola empresa (excepto `SUPER_ADMIN`, que no pertenece a ninguna en
   particular).

2. **`empresa_id` en todos los catalogos.** `TipoCliente`, `ZonaGeografica`, `TipoCamion`,
   `Producto` y `MetodoTarifa` pasan de catalogos globales a catalogos por empresa (los 6
   metodos de tarifa se clonan automaticamente al crear una empresa nueva). `Flota`,
   `TarifaTransportista` y `Ruta` tambien reciben `empresa_id` por consistencia del filtro,
   aunque ya eran derivables via su transportista/CEDI.

3. **Aislamiento centralizado.** El `empresa_id` nunca se confia si viene del cliente
   (body/query) salvo para `SUPER_ADMIN` -- siempre se toma del usuario autenticado, via
   la dependencia `empresa_actual` (backend/app/auth.py) reusada en todos los endpoints.
   `SUPER_ADMIN` puede pasar `?empresa_id=` para navegar/corregir datos de una empresa
   puntual, o dejarlo vacio para ver todas.

4. **Frontend con login.** Pantalla de login, interceptor de axios que adjunta el token y
   redirige a login si expira, menu lateral y rutas filtradas por rol, pantalla `Usuarios`
   (solo `SUPER_ADMIN`) y un selector "viendo datos de la empresa X" en la cabecera (solo
   `SUPER_ADMIN`).

### Migrar produccion a v4

```bash
psql "<external DATABASE_URL>/flete_db" -f backend/migrate_v4_alter.sql
# desplegar el codigo nuevo, luego:
docker run -it --rm \
  -e DATABASE_URL="<external DATABASE_URL>/flete_db" \
  -e SUPER_ADMIN_EMAIL="tu-correo@ejemplo.com" \
  -e SUPER_ADMIN_PASSWORD="una-contrasena-fuerte" \
  -v "$(pwd)/backend:/app" -w /app python:3.11-slim \
  bash -c "pip install -q -r requirements.txt && python migrate_v4_backfill.py"
```

Esto asigna los datos existentes a la empresa real ya creada, crea una "Empresa Demo 2"
con su propio set de datos autocontenido (para probar que el aislamiento funciona de
verdad), y crea el primer usuario `SUPER_ADMIN`.

**Nota:** `seed.py` (usado para poblar una instalacion nueva desde cero) todavia no fue
actualizado para autenticarse contra v4 -- para datos de prueba en local, usa
`migrate_v4_backfill.py` despues de crear la primera empresa manualmente (crea su propio
set de datos para "Empresa Demo 2" sin pasar por `seed.py`).

### Resetear y re-sembrar la base de datos (v2)

```bash
docker compose down -v
docker compose up -d --build
docker compose exec backend python seed.py
```

Esto crea desde cero las 4 zonas con sus poligonos, los 6 metodos de tarifa (incluyendo
POR_KILOMETRO), y 9 pares de rutas planificada/ejecutada (las 7 de v1, `RUTA-BOG-008` que
demuestra POR_KILOMETRO, y `RUTA-BOG-009` que demuestra tarifas diferenciadas por tipo de
camion), ademas de una prueba automatica que confirma que una tarifa restringida a un camion
rechaza rutas con un camion distinto.
