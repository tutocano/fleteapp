from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import auth
from app.database import get_db
from app.models import models
from app.schemas import schemas

router = APIRouter()

# Roles que pueden LEER maestros de su empresa (necesitan ver clientes,
# transportistas, zonas, etc. para operar). USUARIO_FINAL queda fuera a
# proposito: solo tiene acceso a Mapa de Rutas / Mapa General / Conciliacion.
ROLES_LECTURA_MAESTROS = ["EMPRESA_ADMIN", "INTERFAZ"]
# Roles que pueden CREAR/EDITAR/BORRAR maestros de su empresa.
ROLES_ESCRITURA_MAESTROS = ["EMPRESA_ADMIN"]

# Los 6 metodos de tarifa fijos del sistema. Antes de v4 se sembraban una sola
# vez de forma global (main.py); ahora que MetodoTarifa es por empresa, se
# siembran automaticamente cada vez que se crea una empresa nueva (ver
# sembrar_metodos_tarifa_para_empresa, llamado desde crear_empresa).
METODOS_TARIFA_BASE = [
    ("POR_VIAJE", "Por viaje", "Tarifa fija por viaje completo, sin importar paradas ni distancia"),
    ("POR_PARADA", "Por numero de paradas", "Tarifa por cada parada (cliente) visitada en la ruta"),
    ("POR_ZONA", "Por zona de entrega", "Tarifa de la zona mas alejada/costosa entre los clientes de la ruta"),
    ("POR_PESO_VOLUMEN", "Por volumen o peso entregado", "Tarifa por m3 o por kg entregado, sumando todos los clientes de la ruta"),
    ("POR_TIEMPO_SERVICIO", "Por tiempo de servicio", "Tarifa por hora/minuto de atencion en clientes, sumada en la ruta"),
    ("POR_KILOMETRO", "Por kilometro recorrido", "Tarifa por km recorrido, segun la suma de distancia_km_tramo de las paradas de la ruta"),
]


def sembrar_metodos_tarifa_para_empresa(db: Session, empresa_id: int):
    existentes = {
        m.codigo
        for m in db.query(models.MetodoTarifa).filter(models.MetodoTarifa.empresa_id == empresa_id).all()
    }
    for codigo, nombre, descripcion in METODOS_TARIFA_BASE:
        if codigo not in existentes:
            db.add(
                models.MetodoTarifa(
                    empresa_id=empresa_id, codigo=codigo, nombre=nombre, descripcion=descripcion
                )
            )
    db.commit()


def _verificar_pertenencia(obj, empresa_id: Optional[int], tag: str):
    """Lanza 404 si el objeto no existe o (cuando hay filtro de empresa) no le
    pertenece. Se usa tanto para el CRUD generico como para validar llaves
    foraneas al crear registros que referencian otras tablas (ej. una tarifa
    que referencia un transportista)."""
    if obj is None or (empresa_id is not None and obj.empresa_id != empresa_id):
        raise HTTPException(status_code=404, detail=f"{tag} no encontrado")
    return obj


def _crud_router(
    prefix: str,
    tag: str,
    model,
    create_schema,
    out_schema,
    roles_lectura=ROLES_LECTURA_MAESTROS,
    roles_escritura=ROLES_ESCRITURA_MAESTROS,
):
    sub = APIRouter(prefix=prefix, tags=[tag])

    @sub.get("/", response_model=List[out_schema])
    def listar(
        db: Session = Depends(get_db),
        usuario: models.Usuario = Depends(auth.require_role(*roles_lectura)),
        empresa_id: Optional[int] = Depends(auth.empresa_actual),
    ):
        q = db.query(model)
        if empresa_id is not None:
            q = q.filter(model.empresa_id == empresa_id)
        return q.all()

    @sub.get("/{item_id}", response_model=out_schema)
    def obtener(
        item_id: int,
        db: Session = Depends(get_db),
        usuario: models.Usuario = Depends(auth.require_role(*roles_lectura)),
        empresa_id: Optional[int] = Depends(auth.empresa_actual),
    ):
        obj = db.query(model).get(item_id)
        return _verificar_pertenencia(obj, empresa_id, tag)

    @sub.post("/", response_model=out_schema)
    def crear(
        payload: create_schema,
        db: Session = Depends(get_db),
        usuario: models.Usuario = Depends(auth.require_role(*roles_escritura)),
        empresa_id: Optional[int] = Depends(auth.empresa_actual),
    ):
        if empresa_id is None:
            raise HTTPException(
                status_code=400,
                detail="Como SUPER_ADMIN, indica ?empresa_id= para saber a que empresa pertenece este registro",
            )
        obj = model(**payload.model_dump(), empresa_id=empresa_id)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    @sub.put("/{item_id}", response_model=out_schema)
    def actualizar(
        item_id: int,
        payload: create_schema,
        db: Session = Depends(get_db),
        usuario: models.Usuario = Depends(auth.require_role(*roles_escritura)),
        empresa_id: Optional[int] = Depends(auth.empresa_actual),
    ):
        obj = db.query(model).get(item_id)
        _verificar_pertenencia(obj, empresa_id, tag)
        for k, v in payload.model_dump().items():
            setattr(obj, k, v)
        db.commit()
        db.refresh(obj)
        return obj

    @sub.delete("/{item_id}")
    def eliminar(
        item_id: int,
        db: Session = Depends(get_db),
        usuario: models.Usuario = Depends(auth.require_role(*roles_escritura)),
        empresa_id: Optional[int] = Depends(auth.empresa_actual),
    ):
        obj = db.query(model).get(item_id)
        _verificar_pertenencia(obj, empresa_id, tag)
        db.delete(obj)
        db.commit()
        return {"ok": True}

    return sub


# ---------- Empresa: solo SUPER_ADMIN (no tiene empresa_id propio) ----------
empresa_router = APIRouter(prefix="/empresas", tags=["Empresa"])


@empresa_router.get("/", response_model=List[schemas.EmpresaOut])
def listar_empresas(db: Session = Depends(get_db), usuario: models.Usuario = Depends(auth.require_role())):
    return db.query(models.Empresa).all()


@empresa_router.get("/{empresa_id}", response_model=schemas.EmpresaOut)
def obtener_empresa(
    empresa_id: int, db: Session = Depends(get_db), usuario: models.Usuario = Depends(auth.require_role())
):
    obj = db.query(models.Empresa).get(empresa_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return obj


@empresa_router.post("/", response_model=schemas.EmpresaOut)
def crear_empresa(
    payload: schemas.EmpresaCreate,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(auth.require_role()),
):
    obj = models.Empresa(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    # v4: al crear una empresa nueva se le clonan automaticamente los 6 metodos
    # de tarifa fijos, porque MetodoTarifa ahora es por empresa (ver seccion
    # "Implicacion de que MetodoTarifa sea por empresa" en el plan v4).
    sembrar_metodos_tarifa_para_empresa(db, obj.id)
    return obj


@empresa_router.put("/{empresa_id}", response_model=schemas.EmpresaOut)
def actualizar_empresa(
    empresa_id: int,
    payload: schemas.EmpresaCreate,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(auth.require_role()),
):
    obj = db.query(models.Empresa).get(empresa_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    for k, v in payload.model_dump().items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@empresa_router.delete("/{empresa_id}")
def eliminar_empresa(
    empresa_id: int, db: Session = Depends(get_db), usuario: models.Usuario = Depends(auth.require_role())
):
    obj = db.query(models.Empresa).get(empresa_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    db.delete(obj)
    db.commit()
    return {"ok": True}


cedi_router = _crud_router(
    "/centros-distribucion",
    "CentroDistribucion",
    models.CentroDistribucion,
    schemas.CentroDistribucionCreate,
    schemas.CentroDistribucionOut,
)
tipo_cliente_router = _crud_router(
    "/tipos-cliente",
    "TipoCliente",
    models.TipoCliente,
    schemas.TipoClienteCreate,
    schemas.TipoClienteOut,
)
zona_router = _crud_router(
    "/zonas-geograficas",
    "ZonaGeografica",
    models.ZonaGeografica,
    schemas.ZonaGeograficaCreate,
    schemas.ZonaGeograficaOut,
)
cliente_router = _crud_router(
    "/clientes", "Cliente", models.Cliente, schemas.ClienteCreate, schemas.ClienteOut
)
tipo_camion_router = _crud_router(
    "/tipos-camion",
    "TipoCamion",
    models.TipoCamion,
    schemas.TipoCamionCreate,
    schemas.TipoCamionOut,
)
transportista_router = _crud_router(
    "/transportistas",
    "Transportista",
    models.Transportista,
    schemas.TransportistaCreate,
    schemas.TransportistaOut,
)
flota_router = _crud_router(
    "/flota", "Flota", models.Flota, schemas.FlotaCreate, schemas.FlotaOut
)
producto_router = _crud_router(
    "/productos", "Producto", models.Producto, schemas.ProductoCreate, schemas.ProductoOut
)


# Metodo tarifa: solo lectura (catalogo fijo, se siembra solo al crear la empresa)
metodo_tarifa_router = APIRouter(prefix="/metodos-tarifa", tags=["MetodoTarifa"])


@metodo_tarifa_router.get("/", response_model=List[schemas.MetodoTarifaOut])
def listar_metodos(
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(auth.require_role(*ROLES_LECTURA_MAESTROS)),
    empresa_id: Optional[int] = Depends(auth.empresa_actual),
):
    q = db.query(models.MetodoTarifa)
    if empresa_id is not None:
        q = q.filter(models.MetodoTarifa.empresa_id == empresa_id)
    return q.all()


# Tarifa transportista: CRUD con manejo especial de zonas_detalle
tarifa_router = APIRouter(prefix="/tarifas-transportista", tags=["TarifaTransportista"])


@tarifa_router.get("/", response_model=List[schemas.TarifaTransportistaOut])
def listar_tarifas(
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(auth.require_role(*ROLES_LECTURA_MAESTROS)),
    empresa_id: Optional[int] = Depends(auth.empresa_actual),
):
    q = db.query(models.TarifaTransportista)
    if empresa_id is not None:
        q = q.filter(models.TarifaTransportista.empresa_id == empresa_id)
    return q.all()


@tarifa_router.get("/{tarifa_id}", response_model=schemas.TarifaTransportistaOut)
def obtener_tarifa(
    tarifa_id: int,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(auth.require_role(*ROLES_LECTURA_MAESTROS)),
    empresa_id: Optional[int] = Depends(auth.empresa_actual),
):
    obj = db.query(models.TarifaTransportista).get(tarifa_id)
    return _verificar_pertenencia(obj, empresa_id, "Tarifa")


@tarifa_router.post("/", response_model=schemas.TarifaTransportistaOut)
def crear_tarifa(
    payload: schemas.TarifaTransportistaCreate,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(auth.require_role(*ROLES_ESCRITURA_MAESTROS)),
    empresa_id: Optional[int] = Depends(auth.empresa_actual),
):
    if empresa_id is None:
        raise HTTPException(
            status_code=400,
            detail="Como SUPER_ADMIN, indica ?empresa_id= para saber a que empresa pertenece esta tarifa",
        )
    transportista = db.query(models.Transportista).get(payload.transportista_id)
    _verificar_pertenencia(transportista, empresa_id, "Transportista")
    metodo = db.query(models.MetodoTarifa).get(payload.metodo_tarifa_id)
    _verificar_pertenencia(metodo, empresa_id, "MetodoTarifa")
    if payload.tipo_camion_id is not None:
        tipo_camion = db.query(models.TipoCamion).get(payload.tipo_camion_id)
        _verificar_pertenencia(tipo_camion, empresa_id, "TipoCamion")

    data = payload.model_dump(exclude={"zonas_detalle"})
    obj = models.TarifaTransportista(**data, empresa_id=empresa_id)
    db.add(obj)
    db.flush()
    if payload.zonas_detalle:
        for zd in payload.zonas_detalle:
            zona = db.query(models.ZonaGeografica).get(zd.zona_geografica_id)
            _verificar_pertenencia(zona, empresa_id, "ZonaGeografica")
            db.add(
                models.TarifaZonaDetalle(
                    tarifa_transportista_id=obj.id,
                    zona_geografica_id=zd.zona_geografica_id,
                    valor=zd.valor,
                )
            )
    db.commit()
    db.refresh(obj)
    return obj


@tarifa_router.put("/{tarifa_id}", response_model=schemas.TarifaTransportistaOut)
def actualizar_tarifa(
    tarifa_id: int,
    payload: schemas.TarifaTransportistaCreate,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(auth.require_role(*ROLES_ESCRITURA_MAESTROS)),
    empresa_id: Optional[int] = Depends(auth.empresa_actual),
):
    obj = db.query(models.TarifaTransportista).get(tarifa_id)
    _verificar_pertenencia(obj, empresa_id, "Tarifa")
    empresa_obj = empresa_id if empresa_id is not None else obj.empresa_id

    transportista = db.query(models.Transportista).get(payload.transportista_id)
    _verificar_pertenencia(transportista, empresa_obj, "Transportista")
    metodo = db.query(models.MetodoTarifa).get(payload.metodo_tarifa_id)
    _verificar_pertenencia(metodo, empresa_obj, "MetodoTarifa")
    if payload.tipo_camion_id is not None:
        tipo_camion = db.query(models.TipoCamion).get(payload.tipo_camion_id)
        _verificar_pertenencia(tipo_camion, empresa_obj, "TipoCamion")

    data = payload.model_dump(exclude={"zonas_detalle"})
    for k, v in data.items():
        setattr(obj, k, v)
    if payload.zonas_detalle is not None:
        db.query(models.TarifaZonaDetalle).filter(
            models.TarifaZonaDetalle.tarifa_transportista_id == tarifa_id
        ).delete()
        for zd in payload.zonas_detalle:
            zona = db.query(models.ZonaGeografica).get(zd.zona_geografica_id)
            _verificar_pertenencia(zona, empresa_obj, "ZonaGeografica")
            db.add(
                models.TarifaZonaDetalle(
                    tarifa_transportista_id=tarifa_id,
                    zona_geografica_id=zd.zona_geografica_id,
                    valor=zd.valor,
                )
            )
    db.commit()
    db.refresh(obj)
    return obj


@tarifa_router.delete("/{tarifa_id}")
def eliminar_tarifa(
    tarifa_id: int,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(auth.require_role(*ROLES_ESCRITURA_MAESTROS)),
    empresa_id: Optional[int] = Depends(auth.empresa_actual),
):
    obj = db.query(models.TarifaTransportista).get(tarifa_id)
    _verificar_pertenencia(obj, empresa_id, "Tarifa")
    db.delete(obj)
    db.commit()
    return {"ok": True}


# Cobertura de zonas por transportista (v3): relacion informativa, no bloquea
# import de rutas. GET devuelve la lista actual; PUT reemplaza el conjunto completo
# (patron "checklist" comodo para el frontend: enviar todos los ids marcados).
cobertura_router = APIRouter(prefix="/transportistas", tags=["Cobertura"])


@cobertura_router.get(
    "/{transportista_id}/zonas-cobertura",
    response_model=List[schemas.TransportistaZonaCoberturaOut],
)
def listar_cobertura(
    transportista_id: int,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(auth.require_role(*ROLES_LECTURA_MAESTROS)),
    empresa_id: Optional[int] = Depends(auth.empresa_actual),
):
    transportista = db.query(models.Transportista).get(transportista_id)
    _verificar_pertenencia(transportista, empresa_id, "Transportista")
    return (
        db.query(models.TransportistaZonaCobertura)
        .filter(models.TransportistaZonaCobertura.transportista_id == transportista_id)
        .all()
    )


@cobertura_router.put(
    "/{transportista_id}/zonas-cobertura",
    response_model=List[schemas.TransportistaZonaCoberturaOut],
)
def actualizar_cobertura(
    transportista_id: int,
    payload: schemas.ZonasCoberturaUpdate,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(auth.require_role(*ROLES_ESCRITURA_MAESTROS)),
    empresa_id: Optional[int] = Depends(auth.empresa_actual),
):
    transportista = db.query(models.Transportista).get(transportista_id)
    _verificar_pertenencia(transportista, empresa_id, "Transportista")
    empresa_obj = empresa_id if empresa_id is not None else transportista.empresa_id

    ids_validos = {
        z.id
        for z in db.query(models.ZonaGeografica.id)
        .filter(models.ZonaGeografica.id.in_(payload.zona_geografica_ids))
        .filter(models.ZonaGeografica.empresa_id == empresa_obj)
        .all()
    }
    faltantes = set(payload.zona_geografica_ids) - ids_validos
    if faltantes:
        raise HTTPException(
            status_code=400, detail=f"Zonas geograficas inexistentes: {sorted(faltantes)}"
        )

    db.query(models.TransportistaZonaCobertura).filter(
        models.TransportistaZonaCobertura.transportista_id == transportista_id
    ).delete()
    for zona_id in payload.zona_geografica_ids:
        db.add(
            models.TransportistaZonaCobertura(
                transportista_id=transportista_id, zona_geografica_id=zona_id
            )
        )
    db.commit()
    return (
        db.query(models.TransportistaZonaCobertura)
        .filter(models.TransportistaZonaCobertura.transportista_id == transportista_id)
        .all()
    )
