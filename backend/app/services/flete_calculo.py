"""
Servicio de calculo de costo de flete.

Implementa los 5 metodos de tarifa:
1. POR_VIAJE: tarifa fija, sin importar paradas/distancia.
2. POR_PARADA: tarifa * numero de paradas (clientes visitados).
3. POR_ZONA: tarifa de la zona MAS COSTOSA entre todos los clientes de la ruta.
4. POR_PESO_VOLUMEN: tarifa * (peso total en kg o volumen total en m3, segun `unidad`).
5. POR_TIEMPO_SERVICIO: tarifa * tiempo total de servicio (en minutos u horas, segun `unidad`).
"""
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy.orm import Session

from app.models.models import Ruta, ParadaRuta, TarifaTransportista, TarifaZonaDetalle


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


def calcular_costo_ruta(db: Session, ruta: Ruta) -> DetalleCalculo:
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
            variables={"valor_unitario": tarifa.valor_unitario},
        )

    if metodo_codigo == "POR_PARADA":
        costo = tarifa.valor_unitario * num_paradas
        return DetalleCalculo(
            metodo=metodo_codigo,
            costo_total=round(costo, 2),
            explicacion=(
                f"{num_paradas} paradas x ${tarifa.valor_unitario:,.2f} c/u = ${costo:,.2f}"
            ),
            variables={"num_paradas": num_paradas, "valor_unitario": tarifa.valor_unitario},
        )

    if metodo_codigo == "POR_ZONA":
        # Determinar la zona de cada cliente de la ruta, cruzar contra la tabla
        # de tarifas por zona del transportista, y tomar el valor MAXIMO.
        zonas_detalle = {zd.zona_geografica_id: zd.valor for zd in tarifa.zonas_detalle}
        max_valor = 0.0
        max_zona_nombre = None
        max_cliente_nombre = None
        detalle_por_parada = []
        for parada in paradas:
            cliente = parada.cliente
            zona_id = cliente.zona_geografica_id
            valor_zona = zonas_detalle.get(zona_id)
            if valor_zona is None:
                # Si el transportista no tiene tarifa definida para esa zona,
                # se usa la tarifa base de la zona como respaldo.
                valor_zona = cliente.zona_geografica.tarifa_zona if cliente.zona_geografica else 0.0
            detalle_por_parada.append(
                {
                    "cliente": cliente.nombre,
                    "zona": cliente.zona_geografica.nombre if cliente.zona_geografica else None,
                    "valor_zona": valor_zona,
                }
            )
            if valor_zona > max_valor:
                max_valor = valor_zona
                max_zona_nombre = cliente.zona_geografica.nombre if cliente.zona_geografica else None
                max_cliente_nombre = cliente.nombre
        return DetalleCalculo(
            metodo=metodo_codigo,
            costo_total=round(max_valor, 2),
            explicacion=(
                f"Zona mas costosa: '{max_zona_nombre}' (cliente {max_cliente_nombre}) "
                f"= ${max_valor:,.2f}. Se aplica esta tarifa al viaje completo."
            ),
            variables={"detalle_por_parada": detalle_por_parada, "max_valor": max_valor},
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

    raise ValueError(f"Metodo de tarifa no soportado: {metodo_codigo}")


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
