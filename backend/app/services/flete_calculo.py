"""
Servicio de calculo de costo de flete.

Implementa los 6 metodos de tarifa:
1. POR_VIAJE: tarifa fija, sin importar paradas/distancia.
2. POR_PARADA: tarifa * numero de paradas (clientes visitados).
3. POR_ZONA: tarifa de la zona MAS COSTOSA entre todos los clientes de la ruta.
   La zona de cada parada se determina automaticamente por punto-en-poligono
   (ver app.services.geo) usando las coordenadas del cliente; si el punto no
   cae en ningun poligono se usa como respaldo el zona_geografica_id manual
   del cliente, dejando trazabilidad de cuando se uso el respaldo.
4. POR_PESO_VOLUMEN: tarifa * (peso total en kg o volumen total en m3, segun `unidad`).
5. POR_TIEMPO_SERVICIO: tarifa * tiempo total de servicio (en minutos u horas, segun `unidad`).
6. POR_KILOMETRO: tarifa * distancia total recorrida en la ruta (suma de
   distancia_km_tramo de todas las paradas de ESA ruta especifica: funciona
   igual para planificada y ejecutada, cada una con sus propias distancias).
"""
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy.orm import Session

from app.models.models import Ruta, ParadaRuta, TarifaTransportista, TarifaZonaDetalle, ZonaGeografica
from app.services.geo import determinar_zona


@dataclass
class DetalleCalculo:
    metodo: str
    costo_total: float
    explicacion: str
    variables: dict = field(default_factory=dict)


def _totales_pedidos(parada: ParadaRuta):
    peso_total = 0.0
    volumen_total = 0.0
    for pedido in parada.pedidos:
        peso_total += pedido.peso_kg or 0.0
        volumen_total += pedido.volumen_m3 or 0.0
    return peso_total, volumen_total


def _calcular_costo_por_metodo(db: Session, ruta: Ruta) -> DetalleCalculo:
    tarifa: TarifaTransportista = ruta.tarifa_transportista
    metodo_codigo = tarifa.metodo_tarifa.codigo
    paradas = sorted(ruta.paradas, key=lambda p: p.secuencia)
    num_paradas = len(paradas)

    if metodo_codigo == "POR_VIAJE":
        costo = tarifa.valor_unitario
        return DetalleCalculo(
            metodo=metodo_codigo,
            costo_total=round(costo, 2),
            explicacion=f"Tarifa fija por viaje completo: ${tarifa.valor_unitario:,.2f}",
            variables={
                "valor_unitario": tarifa.valor_unitario,
                "unidad": "VIAJE",
                "base_calculo": 1,
            },
        )

    if metodo_codigo == "POR_PARADA":
        costo = tarifa.valor_unitario * num_paradas
        return DetalleCalculo(
            metodo=metodo_codigo,
            costo_total=round(costo, 2),
            explicacion=(
                f"{num_paradas} paradas x ${tarifa.valor_unitario:,.2f} c/u = ${costo:,.2f}"
            ),
            variables={
                "num_paradas": num_paradas,
                "valor_unitario": tarifa.valor_unitario,
                "unidad": "PARADA",
                "base_calculo": num_paradas,
            },
        )

    if metodo_codigo == "POR_ZONA":
        # Determinar la zona de cada cliente de la ruta mediante punto-en-poligono
        # (algoritmo de ray casting sobre ZonaGeografica.poligono), cruzar contra
        # la tabla de tarifas por zona del transportista, y tomar el valor MAXIMO.
        zonas_detalle = {zd.zona_geografica_id: zd.valor for zd in tarifa.zonas_detalle}
        todas_zonas = db.query(ZonaGeografica).all()
        max_valor = 0.0
        max_zona_nombre = None
        max_cliente_nombre = None
        detalle_por_parada = []
        for parada in paradas:
            cliente = parada.cliente
            zona_detectada = determinar_zona(cliente.latitud, cliente.longitud, todas_zonas)
            uso_respaldo_manual = False
            if zona_detectada is not None:
                zona_efectiva = zona_detectada
            elif cliente.zona_geografica is not None:
                # Caso borde: el punto no cayo en ningun poligono. Se usa como
                # respaldo el zona_geografica_id asignado manualmente al cliente,
                # dejando registro explicito de que se aplico el respaldo.
                zona_efectiva = cliente.zona_geografica
                uso_respaldo_manual = True
            else:
                zona_efectiva = None

            zona_id = zona_efectiva.id if zona_efectiva else None
            valor_zona = zonas_detalle.get(zona_id)
            if valor_zona is None:
                # Si el transportista no tiene tarifa definida para esa zona,
                # se usa la tarifa base de la zona como respaldo.
                valor_zona = zona_efectiva.tarifa_zona if zona_efectiva else 0.0

            detalle_por_parada.append(
                {
                    "cliente": cliente.nombre,
                    "zona_por_poligono": zona_detectada.nombre if zona_detectada else None,
                    "zona_aplicada": zona_efectiva.nombre if zona_efectiva else None,
                    "uso_respaldo_manual": uso_respaldo_manual,
                    "valor_zona": valor_zona,
                }
            )
            if valor_zona > max_valor:
                max_valor = valor_zona
                max_zona_nombre = zona_efectiva.nombre if zona_efectiva else None
                max_cliente_nombre = cliente.nombre
        return DetalleCalculo(
            metodo=metodo_codigo,
            costo_total=round(max_valor, 2),
            explicacion=(
                f"Zona mas costosa: '{max_zona_nombre}' (cliente {max_cliente_nombre}, "
                f"detectada por poligono) = ${max_valor:,.2f}. Se aplica esta tarifa al viaje completo."
            ),
            variables={
                "detalle_por_parada": detalle_por_parada,
                "max_valor": max_valor,
                "zona_aplicada": max_zona_nombre,
                "unidad": "ZONA",
                "valor_unitario": max_valor,
                "base_calculo": 1,
            },
        )

    if metodo_codigo == "POR_PESO_VOLUMEN":
        peso_total = 0.0
        volumen_total = 0.0
        for parada in paradas:
            p, v = _totales_pedidos(parada)
            peso_total += p
            volumen_total += v
        unidad = (tarifa.unidad or "KG").upper()
        if unidad == "M3":
            base = volumen_total
            costo = tarifa.valor_unitario * volumen_total
            explicacion = (
                f"{volumen_total:,.3f} m3 entregados x ${tarifa.valor_unitario:,.2f}/m3 = ${costo:,.2f}"
            )
        else:
            base = peso_total
            costo = tarifa.valor_unitario * peso_total
            explicacion = (
                f"{peso_total:,.2f} kg entregados x ${tarifa.valor_unitario:,.2f}/kg = ${costo:,.2f}"
            )
        return DetalleCalculo(
            metodo=metodo_codigo,
            costo_total=round(costo, 2),
            explicacion=explicacion,
            variables={
                "peso_total_kg": peso_total,
                "volumen_total_m3": volumen_total,
                "unidad": unidad,
                "base_calculo": base,
                "valor_unitario": tarifa.valor_unitario,
            },
        )

    if metodo_codigo == "POR_TIEMPO_SERVICIO":
        tiempo_total_min = sum(p.tiempo_servicio_min or 0.0 for p in paradas)
        unidad = (tarifa.unidad or "MINUTO").upper()
        if unidad == "HORA":
            base = tiempo_total_min / 60.0
            costo = tarifa.valor_unitario * base
            explicacion = (
                f"{base:,.2f} horas de servicio x ${tarifa.valor_unitario:,.2f}/hora = ${costo:,.2f}"
            )
        else:
            base = tiempo_total_min
            costo = tarifa.valor_unitario * base
            explicacion = (
                f"{base:,.2f} minutos de servicio x ${tarifa.valor_unitario:,.2f}/min = ${costo:,.2f}"
            )
        return DetalleCalculo(
            metodo=metodo_codigo,
            costo_total=round(costo, 2),
            explicacion=explicacion,
            variables={
                "tiempo_total_min": tiempo_total_min,
                "unidad": unidad,
                "base_calculo": base,
                "valor_unitario": tarifa.valor_unitario,
            },
        )

    if metodo_codigo == "POR_KILOMETRO":
        distancia_total_km = sum(p.distancia_km_tramo or 0.0 for p in paradas)
        costo = tarifa.valor_unitario * distancia_total_km
        explicacion = (
            f"{distancia_total_km:,.2f} km recorridos x ${tarifa.valor_unitario:,.2f}/km = ${costo:,.2f}"
        )
        return DetalleCalculo(
            metodo=metodo_codigo,
            costo_total=round(costo, 2),
            explicacion=explicacion,
            variables={
                "distancia_total_km": distancia_total_km,
                "unidad": "KM",
                "base_calculo": distancia_total_km,
                "valor_unitario": tarifa.valor_unitario,
            },
        )

    raise ValueError(f"Metodo de tarifa no soportado: {metodo_codigo}")


def calcular_costo_ruta(db: Session, ruta: Ruta) -> DetalleCalculo:
    """
    Calcula el costo segun el metodo de tarifa (_calcular_costo_por_metodo) y le
    agrega un bloque de COMPARACION entre los datos importados en el JSON de la
    ruta (distancia_km_tramo / tiempo_transito_min_tramo) y los datos de
    REFERENCIA obtenidos siempre del conector Google/Haversine
    (distancia_km_tramo_referencia / tiempo_transito_min_tramo_referencia, ver
    distance_connector.py). Esto aplica a los 6 metodos de tarifa por igual, ya
    que sirve para detectar rutas mal planificadas o mal ejecutadas
    independientemente de si el metodo de tarifa usa la distancia para el costo.
    Solo POR_KILOMETRO usa la distancia en el costo, asi que es el unico metodo
    donde ademas se calcula un costo_con_distancia_referencia alterno.
    """
    detalle = _calcular_costo_por_metodo(db, ruta)
    paradas = sorted(ruta.paradas, key=lambda p: p.secuencia)

    distancia_importada_km = sum(p.distancia_km_tramo or 0.0 for p in paradas)
    distancia_referencia_km = sum(p.distancia_km_tramo_referencia or 0.0 for p in paradas)
    tiempo_importado_min = sum(p.tiempo_transito_min_tramo or 0.0 for p in paradas)
    tiempo_referencia_min = sum(p.tiempo_transito_min_tramo_referencia or 0.0 for p in paradas)
    fuentes_referencia = sorted({p.fuente_referencia for p in paradas if p.fuente_referencia})

    comparacion = {
        "distancia_importada_km": round(distancia_importada_km, 3),
        "distancia_referencia_km": round(distancia_referencia_km, 3),
        "diferencia_distancia_km": round(distancia_referencia_km - distancia_importada_km, 3),
        "tiempo_importado_min": round(tiempo_importado_min, 2),
        "tiempo_referencia_min": round(tiempo_referencia_min, 2),
        "diferencia_tiempo_min": round(tiempo_referencia_min - tiempo_importado_min, 2),
        "fuentes_referencia": fuentes_referencia,
    }

    if detalle.metodo == "POR_KILOMETRO":
        tarifa: TarifaTransportista = ruta.tarifa_transportista
        costo_con_referencia = round(tarifa.valor_unitario * distancia_referencia_km, 2)
        comparacion["costo_con_distancia_importada"] = detalle.costo_total
        comparacion["costo_con_distancia_referencia"] = costo_con_referencia
        comparacion["diferencia_costo"] = round(costo_con_referencia - detalle.costo_total, 2)

    detalle.variables["comparacion_distancia_tiempo"] = comparacion
    return detalle


def calcular_y_guardar(db: Session, ruta: Ruta) -> DetalleCalculo:
    detalle = calcular_costo_ruta(db, ruta)
    ruta.costo_flete_calculado = detalle.costo_total
    ruta.detalle_calculo = {
        "metodo": detalle.metodo,
        "explicacion": detalle.explicacion,
        "variables": detalle.variables,
    }
    db.add(ruta)
    db.commit()
    db.refresh(ruta)
    return detalle
