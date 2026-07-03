"""
Importacion masiva de rutas (planificadas o ejecutadas) via archivo CSV.

Motivo (v4.1): la importacion via JSON (ver rutas.py/_importar_ruta) sigue
siendo la forma mas flexible de cargar UNA ruta a la vez, pero requiere
conocer los IDs internos de base de datos (cliente_id, producto_id, etc.),
lo cual es poco practico para cargar de un tiron TODAS las rutas de un dia
completo de operacion. El CSV resuelve esto de dos formas:

  1. Identifica cada entidad por su codigo/nombre de negocio (el mismo que
     ve el usuario en las pantallas de Clientes, CEDIs, Productos, etc.), no
     por su ID interno -- mas facil de diligenciar y funciona igual en
     cualquier ambiente (local, produccion) sin importar los IDs autogenerados.
  2. Permite varias rutas (con varias paradas y varios pedidos cada una) en
     un solo archivo: una fila = un (pedido dentro de una parada dentro de
     una ruta). Filas con el mismo `codigo_ruta` se agrupan en la misma ruta;
     filas con la misma `codigo_ruta`+`secuencia` se agrupan en la misma parada.

Para las rutas EJECUTADAS, el CSV no pide un ID de "ruta planificada": se
asume la MISMA convencion que ya usa el resto del sistema (ver seed.py/
RutasPage.jsx) de que una ruta ejecutada comparte el mismo `codigo_ruta` que
su ruta planificada. El backend busca automaticamente la ruta planificada
con ese codigo dentro de la misma empresa.

Reutiliza `_importar_ruta` de rutas.py para el guardado real (misma
validacion de negocio, mismo calculo de costo) -- este modulo solo se encarga
de parsear el CSV y resolver codigos/nombres a los `schemas.RutaImport` que
ese endpoint ya sabe procesar.
"""
import csv
import io
from collections import OrderedDict
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import models
from app.schemas import schemas

# Columnas obligatorias que debe traer el CSV (encabezado de la primera fila).
# Las demas columnas mencionadas en el formato son opcionales (se pueden dejar
# vacias en la celda).
COLUMNAS_OBLIGATORIAS = [
    "codigo_ruta",
    "centro_distribucion_codigo",
    "transportista_nombre",
    "tarifa_nombre",
    "tipo_camion_nombre",
    "secuencia",
    "cliente_codigo",
    "producto_codigo",
    "cantidad",
]

COLUMNAS_OPCIONALES = [
    "fecha",
    "flota_placa",
    "tiempo_servicio_min",
    "distancia_km_tramo",
    "tiempo_transito_min_tramo",
    "hora_llegada_estimada",
    "hora_llegada_real",
    "peso_kg",
    "volumen_m3",
]

TODAS_LAS_COLUMNAS = COLUMNAS_OBLIGATORIAS + COLUMNAS_OPCIONALES


class FilaCSVError(Exception):
    """Error al interpretar una fila puntual del CSV (dato invalido o no encontrado)."""


class EncabezadoCSVError(Exception):
    """Error al validar el encabezado del CSV (faltan columnas obligatorias)."""


def _valor(fila: dict, columna: str) -> str:
    return (fila.get(columna) or "").strip()


def _buscar_por_codigo(db: Session, modelo, empresa_id: int, codigo: str, etiqueta: str):
    if not codigo:
        raise FilaCSVError(f"Falta el codigo de {etiqueta}")
    obj = (
        db.query(modelo)
        .filter(modelo.empresa_id == empresa_id, modelo.codigo == codigo)
        .first()
    )
    if not obj:
        raise FilaCSVError(f"No existe {etiqueta} con codigo '{codigo}' en esta empresa")
    return obj


def _buscar_por_nombre(db: Session, modelo, empresa_id: int, nombre: str, etiqueta: str):
    if not nombre:
        raise FilaCSVError(f"Falta el nombre de {etiqueta}")
    coincidencias = (
        db.query(modelo)
        .filter(modelo.empresa_id == empresa_id, func.lower(modelo.nombre) == nombre.lower())
        .all()
    )
    if not coincidencias:
        raise FilaCSVError(f"No existe {etiqueta} con nombre '{nombre}' en esta empresa")
    if len(coincidencias) > 1:
        raise FilaCSVError(
            f"Hay mas de un(a) {etiqueta} con nombre '{nombre}' en esta empresa; "
            "usa un nombre unico para poder identificarlo en el CSV"
        )
    return coincidencias[0]


def _parsear_float_opcional(valor: str) -> Optional[float]:
    if not valor:
        return None
    try:
        return float(valor)
    except ValueError:
        raise FilaCSVError(f"'{valor}' no es un numero valido")


def _parsear_fecha_opcional(valor: str) -> Optional[datetime]:
    if not valor:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(valor, fmt)
        except ValueError:
            continue
    raise FilaCSVError(
        f"Fecha invalida: '{valor}' (usa AAAA-MM-DD, AAAA-MM-DD HH:MM o AAAA-MM-DDTHH:MM:SS)"
    )


def parsear_rutas_csv(
    contenido: bytes, db: Session, empresa_id: int, es_planificada: bool
) -> Tuple[List[Tuple[str, schemas.RutaImport]], List[dict]]:
    """
    Parsea el CSV y arma un `schemas.RutaImport` por cada codigo_ruta distinto.

    Retorna (rutas_ok, errores):
      - rutas_ok: lista de (codigo_ruta, RutaImport) listas para pasar a _importar_ruta.
      - errores: lista de {"fila": int|None, "codigo_ruta": str|None, "error": str}.
        Si una ruta tiene aunque sea una fila con error, esa ruta COMPLETA se
        excluye de rutas_ok (no se importa una ruta con datos parciales).
    """
    try:
        texto = contenido.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise EncabezadoCSVError("El archivo no es un CSV de texto valido (usa codificacion UTF-8)")

    lector = csv.DictReader(io.StringIO(texto))
    encabezado = lector.fieldnames or []
    faltantes = [c for c in COLUMNAS_OBLIGATORIAS if c not in encabezado]
    if faltantes:
        raise EncabezadoCSVError(
            "Faltan columnas obligatorias en el CSV: " + ", ".join(faltantes)
        )

    # codigo_ruta -> datos comunes de la ruta + paradas (agrupadas por secuencia)
    rutas_raw: "OrderedDict[str, dict]" = OrderedDict()
    errores: List[dict] = []
    rutas_con_error = set()

    for num_fila, fila in enumerate(lector, start=2):  # la fila 1 es el encabezado
        codigo_ruta = _valor(fila, "codigo_ruta")
        if not codigo_ruta:
            errores.append({"fila": num_fila, "codigo_ruta": None, "error": "codigo_ruta vacio"})
            continue
        if codigo_ruta in rutas_con_error:
            continue  # ya se supo que esta ruta tiene un error en otra fila; no seguir acumulando

        try:
            centro = _buscar_por_codigo(
                db, models.CentroDistribucion, empresa_id,
                _valor(fila, "centro_distribucion_codigo"), "un Centro de Distribucion",
            )
            transportista = _buscar_por_nombre(
                db, models.Transportista, empresa_id,
                _valor(fila, "transportista_nombre"), "un Transportista",
            )
            tipo_camion = _buscar_por_nombre(
                db, models.TipoCamion, empresa_id,
                _valor(fila, "tipo_camion_nombre"), "un Tipo de Camion",
            )
            tarifa = _buscar_por_nombre(
                db, models.TarifaTransportista, empresa_id,
                _valor(fila, "tarifa_nombre"), "una Tarifa de Transportista",
            )
            cliente = _buscar_por_codigo(
                db, models.Cliente, empresa_id, _valor(fila, "cliente_codigo"), "un Cliente"
            )
            producto = _buscar_por_codigo(
                db, models.Producto, empresa_id, _valor(fila, "producto_codigo"), "un Producto"
            )

            secuencia_txt = _valor(fila, "secuencia")
            if not secuencia_txt.isdigit():
                raise FilaCSVError(f"'secuencia' debe ser un numero entero (recibido: '{secuencia_txt}')")
            secuencia = int(secuencia_txt)

            cantidad = _parsear_float_opcional(_valor(fila, "cantidad"))
            if cantidad is None:
                raise FilaCSVError("Falta 'cantidad'")

            flota = None
            flota_placa = _valor(fila, "flota_placa")
            if flota_placa:
                flota = (
                    db.query(models.Flota)
                    .filter(models.Flota.empresa_id == empresa_id, models.Flota.placa == flota_placa)
                    .first()
                )
                if not flota:
                    raise FilaCSVError(f"No existe Flota con placa '{flota_placa}' en esta empresa")

            fecha = _parsear_fecha_opcional(_valor(fila, "fecha"))
            distancia_km_tramo = _parsear_float_opcional(_valor(fila, "distancia_km_tramo"))
            tiempo_transito_min_tramo = _parsear_float_opcional(_valor(fila, "tiempo_transito_min_tramo"))
            tiempo_servicio_min = _parsear_float_opcional(_valor(fila, "tiempo_servicio_min")) or 0
            hora_llegada_estimada = _parsear_fecha_opcional(_valor(fila, "hora_llegada_estimada"))
            hora_llegada_real = _parsear_fecha_opcional(_valor(fila, "hora_llegada_real"))
            peso_kg = _parsear_float_opcional(_valor(fila, "peso_kg"))
            volumen_m3 = _parsear_float_opcional(_valor(fila, "volumen_m3"))
        except FilaCSVError as e:
            errores.append({"fila": num_fila, "codigo_ruta": codigo_ruta, "error": str(e)})
            rutas_con_error.add(codigo_ruta)
            continue

        ruta_entry = rutas_raw.setdefault(
            codigo_ruta,
            {
                "centro_distribucion_id": centro.id,
                "transportista_id": transportista.id,
                "tarifa_transportista_id": tarifa.id,
                "tipo_camion_id": tipo_camion.id,
                "flota_id": flota.id if flota else None,
                "fecha": fecha,
                "paradas": OrderedDict(),
            },
        )
        parada_entry = ruta_entry["paradas"].setdefault(
            secuencia,
            {
                "cliente_id": cliente.id,
                "secuencia": secuencia,
                "tiempo_servicio_min": tiempo_servicio_min,
                "distancia_km_tramo": distancia_km_tramo,
                "tiempo_transito_min_tramo": tiempo_transito_min_tramo,
                "hora_llegada_estimada": hora_llegada_estimada,
                "hora_llegada_real": hora_llegada_real,
                "pedidos": [],
            },
        )
        parada_entry["pedidos"].append(
            {
                "producto_id": producto.id,
                "cantidad": cantidad,
                "peso_kg": peso_kg,
                "volumen_m3": volumen_m3,
            }
        )

    rutas_ok: List[Tuple[str, schemas.RutaImport]] = []
    for codigo_ruta, datos in rutas_raw.items():
        if codigo_ruta in rutas_con_error:
            continue

        ruta_planificada_id = None
        if not es_planificada:
            rp = (
                db.query(models.Ruta)
                .filter(
                    models.Ruta.empresa_id == empresa_id,
                    models.Ruta.es_planificada.is_(True),
                    models.Ruta.codigo_ruta == codigo_ruta,
                )
                .first()
            )
            if not rp:
                errores.append(
                    {
                        "fila": None,
                        "codigo_ruta": codigo_ruta,
                        "error": (
                            f"No existe una ruta PLANIFICADA con codigo_ruta '{codigo_ruta}' en esta "
                            "empresa. Importa primero el CSV de planificadas con ese mismo codigo_ruta."
                        ),
                    }
                )
                continue
            ruta_planificada_id = rp.id

        paradas = [
            schemas.ParadaImport(
                cliente_id=p["cliente_id"],
                secuencia=p["secuencia"],
                distancia_km_tramo=p["distancia_km_tramo"],
                tiempo_transito_min_tramo=p["tiempo_transito_min_tramo"],
                tiempo_servicio_min=p["tiempo_servicio_min"],
                hora_llegada_estimada=p["hora_llegada_estimada"],
                hora_llegada_real=p["hora_llegada_real"],
                pedidos=[schemas.PedidoImport(**pe) for pe in p["pedidos"]],
            )
            for p in datos["paradas"].values()
        ]
        ruta_import = schemas.RutaImport(
            codigo_ruta=codigo_ruta,
            centro_distribucion_id=datos["centro_distribucion_id"],
            transportista_id=datos["transportista_id"],
            tarifa_transportista_id=datos["tarifa_transportista_id"],
            tipo_camion_id=datos["tipo_camion_id"],
            flota_id=datos["flota_id"],
            fecha=datos["fecha"],
            ruta_planificada_id=ruta_planificada_id,
            paradas=paradas,
        )
        rutas_ok.append((codigo_ruta, ruta_import))

    return rutas_ok, errores
