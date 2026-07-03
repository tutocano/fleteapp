from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import models
from app.schemas import schemas

router = APIRouter()


def _crud_router(
    prefix: str,
    tag: str,
    model,
    create_schema,
    out_schema,
):
    sub = APIRouter(prefix=prefix, tags=[tag])

    @sub.get("/", response_model=List[out_schema])
    def listar(db: Session = Depends(get_db)):
        return db.query(model).all()

    @sub.get("/{item_id}", response_model=out_schema)
    def obtener(item_id: int, db: Session = Depends(get_db)):
        obj = db.query(model).get(item_id)
        if not obj:
            raise HTTPException(status_code=404, detail=f"{tag} no encontrado")
        return obj

    @sub.post("/", response_model=out_schema)
    def crear(payload: create_schema, db: Session = Depends(get_db)):
        obj = model(**payload.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    @sub.put("/{item_id}", response_model=out_schema)
    def actualizar(item_id: int, payload: create_schema, db: Session = Depends(get_db)):
        obj = db.query(model).get(item_id)
        if not obj:
            raise HTTPException(status_code=404, detail=f"{tag} no encontrado")
        for k, v in payload.model_dump().items():
            setattr(obj, k, v)
        db.commit()
        db.refresh(obj)
        return obj

    @sub.delete("/{item_id}")
    def eliminar(item_id: int, db: Session = Depends(get_db)):
        obj = db.query(model).get(item_id)
        if not obj:
            raise HTTPException(status_code=404, detail=f"{tag} no encontrado")
        db.delete(obj)
        db.commit()
        return {"ok": True}

    return sub


empresa_router = _crud_router(
    "/empresas", "Empresa", models.Empresa, schemas.EmpresaCreate, schemas.EmpresaOut
)
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


# Metodo tarifa: solo lectura (catalogo fijo)
metodo_tarifa_router = APIRouter(prefix="/metodos-tarifa", tags=["MetodoTarifa"])


@metodo_tarifa_router.get("/", response_model=List[schemas.MetodoTarifaOut])
def listar_metodos(db: Session = Depends(get_db)):
    return db.query(models.MetodoTarifa).all()


# Tarifa transportista: CRUD con manejo especial de zonas_detalle
tarifa_router = APIRouter(prefix="/tarifas-transportista", tags=["TarifaTransportista"])


@tarifa_router.get("/", response_model=List[schemas.TarifaTransportistaOut])
def listar_tarifas(db: Session = Depends(get_db)):
    return db.query(models.TarifaTransportista).all()


@tarifa_router.get("/{tarifa_id}", response_model=schemas.TarifaTransportistaOut)
def obtener_tarifa(tarifa_id: int, db: Session = Depends(get_db)):
    obj = db.query(models.TarifaTransportista).get(tarifa_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Tarifa no encontrada")
    return obj


@tarifa_router.post("/", response_model=schemas.TarifaTransportistaOut)
def crear_tarifa(payload: schemas.TarifaTransportistaCreate, db: Session = Depends(get_db)):
    data = payload.model_dump(exclude={"zonas_detalle"})
    obj = models.TarifaTransportista(**data)
    db.add(obj)
    db.flush()
    if payload.zonas_detalle:
        for zd in payload.zonas_detalle:
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
    tarifa_id: int, payload: schemas.TarifaTransportistaCreate, db: Session = Depends(get_db)
):
    obj = db.query(models.TarifaTransportista).get(tarifa_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Tarifa no encontrada")
    data = payload.model_dump(exclude={"zonas_detalle"})
    for k, v in data.items():
        setattr(obj, k, v)
    if payload.zonas_detalle is not None:
        db.query(models.TarifaZonaDetalle).filter(
            models.TarifaZonaDetalle.tarifa_transportista_id == tarifa_id
        ).delete()
        for zd in payload.zonas_detalle:
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
def eliminar_tarifa(tarifa_id: int, db: Session = Depends(get_db)):
    obj = db.query(models.TarifaTransportista).get(tarifa_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Tarifa no encontrada")
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
def listar_cobertura(transportista_id: int, db: Session = Depends(get_db)):
    transportista = db.query(models.Transportista).get(transportista_id)
    if not transportista:
        raise HTTPException(status_code=404, detail="Transportista no encontrado")
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
):
    transportista = db.query(models.Transportista).get(transportista_id)
    if not transportista:
        raise HTTPException(status_code=404, detail="Transportista no encontrado")

    ids_validos = {
        z.id
        for z in db.query(models.ZonaGeografica.id)
        .filter(models.ZonaGeografica.id.in_(payload.zona_geografica_ids))
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
