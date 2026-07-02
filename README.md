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
