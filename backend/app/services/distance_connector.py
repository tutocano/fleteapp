"""
Conector "pluggable" de distancia/tiempo entre dos puntos geograficos.

Por defecto usa una formula de Haversine con un factor de correccion vial
(simulando que las carreteras no son linea recta). Si la variable de entorno
GOOGLE_MAPS_API_KEY esta configurada, se usa Google Routes API / Distance
Matrix API para obtener distancia y tiempo reales. Si la llamada a Google
falla por cualquier razon (key invalida, sin red, error temporal), se hace
fallback automatico a Haversine sin romper el calculo.
"""
import logging
import math
import os
from dataclasses import dataclass
from typing import Optional

try:
    import httpx
except ImportError:  # pragma: no cover
    httpx = None

logger = logging.getLogger("fleteapp.distance_connector")

# Factor de correccion vial: las vias reales no son linea recta.
# 1.3 es un valor tipico usado en logistica para zonas urbanas.
ROAD_FACTOR = 1.3

# Velocidad promedio urbana asumida para estimar tiempo de transito (km/h)
VELOCIDAD_PROMEDIO_KMH = 28.0


@dataclass
class DistanciaResultado:
    distancia_km: float
    tiempo_min: float
    fuente: str  # "HAVERSINE_FALLBACK" o "GOOGLE_ROUTES_API"


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0  # radio de la Tierra en km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def _haversine_fallback(lat1: float, lon1: float, lat2: float, lon2: float) -> DistanciaResultado:
    distancia_directa = _haversine_km(lat1, lon1, lat2, lon2)
    distancia_km = round(distancia_directa * ROAD_FACTOR, 3)
    tiempo_min = round((distancia_km / VELOCIDAD_PROMEDIO_KMH) * 60, 2)
    return DistanciaResultado(distancia_km=distancia_km, tiempo_min=tiempo_min, fuente="HAVERSINE_FALLBACK")


def _google_routes_api(lat1: float, lon1: float, lat2: float, lon2: float, api_key: str) -> Optional[DistanciaResultado]:
    """
    Stub de integracion con Google Routes API (computeRoutes) / Distance Matrix API.
    Se deja preparado para produccion; requiere httpx y la API key.
    Retorna None si falla (para permitir fallback automatico).
    """
    if httpx is None:
        return None
    try:
        url = "https://routes.googleapis.com/directions/v2:computeRoutes"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "routes.duration,routes.distanceMeters",
        }
        payload = {
            "origin": {"location": {"latLng": {"latitude": lat1, "longitude": lon1}}},
            "destination": {"location": {"latLng": {"latitude": lat2, "longitude": lon2}}},
            "travelMode": "DRIVE",
        }
        resp = httpx.post(url, json=payload, headers=headers, timeout=8.0, trust_env=False)
        if resp.status_code >= 400:
            # No se relanza la excepcion (el fallback a Haversine debe seguir
            # funcionando), pero se deja un log claro con la causa real -- sin esto
            # es imposible saber por que se esta usando el fallback (ver logs del
            # servicio backend en Render: pestaña "Logs").
            logger.warning(
                "Google Routes API fallo (HTTP %s): %s. Usando fallback Haversine.",
                resp.status_code,
                resp.text[:500],
            )
            return None
        data = resp.json()
        if "routes" not in data or not data["routes"]:
            logger.warning(
                "Google Routes API respondio sin 'routes' (revisa el X-Goog-FieldMask "
                "o si el origen/destino son validos): %s. Usando fallback Haversine.",
                data,
            )
            return None
        route = data["routes"][0]
        distancia_km = route["distanceMeters"] / 1000.0
        duration_str = route["duration"]  # ej "1234s"
        tiempo_seg = float(duration_str.rstrip("s"))
        tiempo_min = tiempo_seg / 60.0
        return DistanciaResultado(
            distancia_km=round(distancia_km, 3),
            tiempo_min=round(tiempo_min, 2),
            fuente="GOOGLE_ROUTES_API",
        )
    except Exception as exc:
        logger.warning("Google Routes API fallo con excepcion: %r. Usando fallback Haversine.", exc)
        return None


def calcular_distancia_tiempo(lat1: float, lon1: float, lat2: float, lon2: float) -> DistanciaResultado:
    """
    Punto de entrada unico del conector. Decide automaticamente la fuente:
    - Si GOOGLE_MAPS_API_KEY esta seteada, intenta Google Routes API.
    - Si no esta seteada, o si la llamada falla, usa Haversine.
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "").strip()
    if api_key:
        resultado = _google_routes_api(lat1, lon1, lat2, lon2, api_key)
        if resultado is not None:
            return resultado
    return _haversine_fallback(lat1, lon1, lat2, lon2)
