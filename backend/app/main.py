import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.models import models  # noqa: F401 - asegura registro de modelos
from app.routers import maestros, rutas, conciliacion, auth_router, usuarios

Base.metadata.create_all(bind=engine)

# v4: el catalogo de metodos de tarifa ya no se siembra de forma global -- ahora
# MetodoTarifa es por empresa, y se siembra automaticamente cada vez que se crea
# una empresa (ver sembrar_metodos_tarifa_para_empresa en routers/maestros.py,
# invocado desde el endpoint POST /api/empresas).

app = FastAPI(
    title="Fleteapp API",
    description="Sistema de gestion y conciliacion de costos de flete",
    version="1.0.0",
)

# Origenes permitidos para CORS. Por defecto solo localhost (desarrollo). En
# produccion se agrega el dominio real del frontend via la variable de entorno
# FRONTEND_ORIGINS (uno o mas, separados por coma), sin tocar codigo -- asi el
# mismo Dockerfile/imagen sirve para local, Render, o cualquier otro host.
_origenes_extra = [
    o.strip() for o in os.getenv("FRONTEND_ORIGINS", "").split(",") if o.strip()
]
_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    *_origenes_extra,
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_origin_regex=r"http://localhost(:\d+)?|http://127\.0\.0\.1(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router, prefix="/api")
app.include_router(usuarios.router, prefix="/api")
app.include_router(maestros.empresa_router, prefix="/api")
app.include_router(maestros.cedi_router, prefix="/api")
app.include_router(maestros.tipo_cliente_router, prefix="/api")
app.include_router(maestros.zona_router, prefix="/api")
app.include_router(maestros.cliente_router, prefix="/api")
app.include_router(maestros.tipo_camion_router, prefix="/api")
app.include_router(maestros.transportista_router, prefix="/api")
app.include_router(maestros.cobertura_router, prefix="/api")
app.include_router(maestros.flota_router, prefix="/api")
app.include_router(maestros.producto_router, prefix="/api")
app.include_router(maestros.metodo_tarifa_router, prefix="/api")
app.include_router(maestros.tarifa_router, prefix="/api")
app.include_router(rutas.router, prefix="/api")
app.include_router(conciliacion.router, prefix="/api")


@app.get("/")
def root():
    return {"status": "ok", "servicio": "fleteapp-backend"}


@app.get("/health")
def health():
    return {"status": "healthy"}
