from collections import defaultdict
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import models
from app.schemas import schemas

router = APIRouter(prefix="/conciliacion", tags=["Conciliacion"])


def _diff_pct(planificado, real):
    if planificado is None or real is None or planificado == 0:
        return None
    return round(((real - planificado) / planificado) * 100, 2)


@router.get("/rutas", response_model=List[schemas.ConciliacionRutaOut])
def conciliacion_por_ruta(db: Session = Depends(get_db)):
    rutas_planificadas = (
        db.query(models.Ruta).filter(models.Ruta.es_planificada.is_(True)).all()
    )
    resultado = []
    for rp in rutas_planificadas:
        ejecutada = (
            db.query(models.Ruta)
            .filter(models.Ruta.ruta_planificada_id == rp.id)
            .filter(models.Ruta.es_planificada.is_(False))
            .first()
        )
        costo_plan = rp.costo_flete_calculado
        costo_real = ejecutada.costo_flete_calculado if ejecutada else None
        diff_abs = None
        if costo_plan is not None and costo_real is not None:
            diff_abs = round(costo_real - costo_plan, 2)
        resultado.append(
            schemas.ConciliacionRutaOut(
                ruta_planificada_id=rp.id,
                ruta_ejecutada_id=ejecutada.id if ejecutada else None,
                codigo_ruta=rp.codigo_ruta,
                transportista_id=rp.transportista_id,
                transportista_nombre=rp.transportista.nombre,
                metodo_tarifa=rp.tarifa_transportista.metodo_tarifa.codigo,
                costo_planificado=costo_plan,
                costo_real=costo_real,
                diferencia_absoluta=diff_abs,
                diferencia_porcentual=_diff_pct(costo_plan, costo_real),
            )
        )
    return resultado


@router.get("/transportistas", response_model=List[schemas.ConciliacionTransportistaOut])
def conciliacion_por_transportista(db: Session = Depends(get_db)):
    rutas_planificadas = (
        db.query(models.Ruta).filter(models.Ruta.es_planificada.is_(True)).all()
    )
    agregados = defaultdict(lambda: {"nombre": "", "plan": 0.0, "real": 0.0, "n": 0})

    for rp in rutas_planificadas:
        ejecutada = (
            db.query(models.Ruta)
            .filter(models.Ruta.ruta_planificada_id == rp.id)
            .filter(models.Ruta.es_planificada.is_(False))
            .first()
        )
        if not ejecutada:
            continue
        costo_plan = rp.costo_flete_calculado or 0.0
        costo_real = ejecutada.costo_flete_calculado or 0.0
        entry = agregados[rp.transportista_id]
        entry["nombre"] = rp.transportista.nombre
        entry["plan"] += costo_plan
        entry["real"] += costo_real
        entry["n"] += 1

    resultado = []
    for transportista_id, datos in agregados.items():
        diff_abs = round(datos["real"] - datos["plan"], 2)
        pct = _diff_pct(datos["plan"], datos["real"])
        resultado.append(
            schemas.ConciliacionTransportistaOut(
                transportista_id=transportista_id,
                transportista_nombre=datos["nombre"],
                total_planificado=round(datos["plan"], 2),
                total_real=round(datos["real"], 2),
                diferencia_absoluta=diff_abs,
                diferencia_porcentual=pct,
                num_rutas=datos["n"],
            )
        )
    return resultado
