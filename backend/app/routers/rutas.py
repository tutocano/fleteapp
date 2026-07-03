from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import models
from app.schemas import schemas
from app.services.flete_calculo import calcular_y_guardar
from app.services.distance_connector import calcular_distancia_tiempo

router = APIRouter(prefix="/rutas", tags=["Ruta"])


def _importar_ruta(payload: schemas.RutaImport, es_planificada: bool, db: Session) -> models.Ruta:
    centro = db.query(models.CentroDistribucion).get(payload.centro_distribucion_id)
    if not centro:
        raise HTTPException(status_code=404, detail="Centro de distribucion no encontrado")

    tarifa = db.query(models.TarifaTransportista).get(payload.tarifa_transportista_id)
    if not tarifa:
        raise HTTPException(status_code=404, detail="Tarifa de transportista no encontrada")

    # Si la tarifa esta restringida a un tipo de camion especifico, la ruta debe
    # usar ese mismo tipo de camion. Si tarifa.tipo_camion_id es None, la tarifa
    # aplica a cualquier camion y no hay nada que validar.
    if tarifa.tipo_camion_id is not None and tarifa.tipo_camion_id != payload.tipo_camion_id:
        tarifa_camion_nombre = tarifa.tipo_camion.nombre if tarifa.tipo_camion else tarifa.tipo_camion_id
        raise HTTPException(
            status_code=400,
            detail=(
                f"La tarifa '{tarifa.nombre}' solo aplica para camion tipo "
                f"'{tarifa_camion_nombre}', pero la ruta especifica un tipo de camion distinto "
                f"(id {payload.tipo_camion_id}). Selecciona la tarifa correcta para ese camion "
                f"o una tarifa generica (sin tipo de camion asignado)."
            ),
        )

    if not payload.paradas:
        raise HTTPException(status_code=400, detail="La ruta debe tener al menos una parada")

    if not es_planificada and not payload.ruta_planificada_id:
        raise HTTPException(
            status_code=400,
            detail="Una ruta ejecutada debe referenciar su ruta_planificada_id",
        )

    ruta = models.Ruta(
        codigo_ruta=payload.codigo_ruta,
        es_planificada=es_planificada,
        ruta_planificada_id=payload.ruta_planificada_id,
        centro_distribucion_id=payload.centro_distribucion_id,
        transportista_id=payload.transportista_id,
        tarifa_transportista_id=payload.tarifa_transportista_id,
        tipo_camion_id=payload.tipo_camion_id,
        flota_id=payload.flota_id,
        fecha=payload.fecha or datetime.utcnow(),
        estado="EJECUTADA" if not es_planificada else "PLANIFICADA",
    )
    db.add(ruta)
    db.flush()

    paradas_ordenadas = sorted(payload.paradas, key=lambda p: p.secuencia)
    punto_anterior = (centro.latitud, centro.longitud)

    for parada_in in paradas_ordenadas:
        cliente = db.query(models.Cliente).get(parada_in.cliente_id)
        if not cliente:
            raise HTTPException(
                status_code=404, detail=f"Cliente {parada_in.cliente_id} no encontrado"
            )

        distancia_km = parada_in.distancia_km_tramo
        tiempo_min = parada_in.tiempo_transito_min_tramo

        # v3: se llama SIEMPRE al conector de distancia (Google/Haversine), sin
        # importar si el JSON ya trae distancia_km_tramo/tiempo_transito_min_tramo,
        # para tener un dato de referencia objetivo con el que comparar lo importado
        # (permite detectar rutas mal planificadas o mal ejecutadas). Si el JSON no
        # trae valores, el resultado del conector se usa tambien como valor principal
        # (comportamiento identico al de v1/v2).
        resultado_referencia = calcular_distancia_tiempo(
            punto_anterior[0], punto_anterior[1], cliente.latitud, cliente.longitud
        )
        if distancia_km is None:
            distancia_km = resultado_referencia.distancia_km
        if tiempo_min is None:
            tiempo_min = resultado_referencia.tiempo_min

        parada = models.ParadaRuta(
            ruta_id=ruta.id,
            cliente_id=cliente.id,
            secuencia=parada_in.secuencia,
            distancia_km_tramo=distancia_km,
            tiempo_transito_min_tramo=tiempo_min,
            distancia_km_tramo_referencia=resultado_referencia.distancia_km,
            tiempo_transito_min_tramo_referencia=resultado_referencia.tiempo_min,
            fuente_referencia=resultado_referencia.fuente,
            tiempo_servicio_min=parada_in.tiempo_servicio_min,
            hora_llegada_estimada=parada_in.hora_llegada_estimada,
            hora_llegada_real=parada_in.hora_llegada_real,
        )
        db.add(parada)
        db.flush()

        for pedido_in in parada_in.pedidos:
            producto = db.query(models.Producto).get(pedido_in.producto_id)
            if not producto:
                raise HTTPException(
                    status_code=404, detail=f"Producto {pedido_in.producto_id} no encontrado"
                )
            peso_kg = (
                pedido_in.peso_kg
                if pedido_in.peso_kg is not None
                else producto.peso_unitario_kg * pedido_in.cantidad
            )
            volumen_m3 = (
                pedido_in.volumen_m3
                if pedido_in.volumen_m3 is not None
                else producto.volumen_unitario_m3 * pedido_in.cantidad
            )
            db.add(
                models.PedidoClienteRuta(
                    parada_ruta_id=parada.id,
                    producto_id=producto.id,
                    cantidad=pedido_in.cantidad,
                    peso_kg=peso_kg,
                    volumen_m3=volumen_m3,
                )
            )

        punto_anterior = (cliente.latitud, cliente.longitud)

    db.commit()
    db.refresh(ruta)

    calcular_y_guardar(db, ruta)
    db.refresh(ruta)
    return ruta


@router.post("/importar/planificada", response_model=schemas.RutaOut)
def importar_ruta_planificada(payload: schemas.RutaImport, db: Session = Depends(get_db)):
    ruta = _importar_ruta(payload, es_planificada=True, db=db)
    return ruta


@router.post("/importar/ejecutada", response_model=schemas.RutaOut)
def importar_ruta_ejecutada(payload: schemas.RutaImport, db: Session = Depends(get_db)):
    ruta = _importar_ruta(payload, es_planificada=False, db=db)
    return ruta


@router.get("/", response_model=List[schemas.RutaListOut])
def listar_rutas(es_planificada: Optional[bool] = None, db: Session = Depends(get_db)):
    q = db.query(models.Ruta)
    if es_planificada is not None:
        q = q.filter(models.Ruta.es_planificada == es_planificada)
    return q.order_by(models.Ruta.id.desc()).all()


@router.get("/{ruta_id}", response_model=schemas.RutaOut)
def obtener_ruta(ruta_id: int, db: Session = Depends(get_db)):
    ruta = (
        db.query(models.Ruta)
        .options(joinedload(models.Ruta.paradas).joinedload(models.ParadaRuta.pedidos))
        .options(joinedload(models.Ruta.paradas).joinedload(models.ParadaRuta.cliente))
        .options(joinedload(models.Ruta.centro_distribucion))
        .options(joinedload(models.Ruta.tipo_camion))
        .get(ruta_id)
    )
    if not ruta:
        raise HTTPException(status_code=404, detail="Ruta no encontrada")
    return ruta


@router.post("/{ruta_id}/recalcular", response_model=schemas.RutaOut)
def recalcular_ruta(ruta_id: int, db: Session = Depends(get_db)):
    ruta = db.query(models.Ruta).get(ruta_id)
    if not ruta:
        raise HTTPException(status_code=404, detail="Ruta no encontrada")
    calcular_y_guardar(db, ruta)
    db.refresh(ruta)
    return ruta


@router.get("/{ruta_id}/mapa")
def datos_mapa_ruta(ruta_id: int, db: Session = Depends(get_db)):
    """Devuelve los puntos (CEDI + clientes en secuencia) para pintar la polilinea en el mapa."""
    ruta = (
        db.query(models.Ruta)
        .options(joinedload(models.Ruta.paradas).joinedload(models.ParadaRuta.cliente))
        .options(joinedload(models.Ruta.centro_distribucion))
        .get(ruta_id)
    )
    if not ruta:
        raise HTTPException(status_code=404, detail="Ruta no encontrada")

    puntos = [
        {
            "tipo": "CEDI",
            "nombre": ruta.centro_distribucion.nombre,
            "lat": ruta.centro_distribucion.latitud,
            "lon": ruta.centro_distribucion.longitud,
        }
    ]
    for parada in sorted(ruta.paradas, key=lambda p: p.secuencia):
        puntos.append(
            {
                "tipo": "CLIENTE",
                "nombre": parada.cliente.nombre,
                "lat": parada.cliente.latitud,
                "lon": parada.cliente.longitud,
                "secuencia": parada.secuencia,
                "distancia_km_tramo": parada.distancia_km_tramo,
                "tiempo_transito_min_tramo": parada.tiempo_transito_min_tramo,
                "distancia_km_tramo_referencia": parada.distancia_km_tramo_referencia,
                "tiempo_transito_min_tramo_referencia": parada.tiempo_transito_min_tramo_referencia,
                "fuente_referencia": parada.fuente_referencia,
                "tiempo_servicio_min": parada.tiempo_servicio_min,
            }
        )
    return {
        "ruta_id": ruta.id,
        "codigo_ruta": ruta.codigo_ruta,
        "es_planificada": ruta.es_planificada,
        "puntos": puntos,
    }
