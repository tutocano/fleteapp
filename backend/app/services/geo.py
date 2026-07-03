"""
Utilidades geoespaciales en Python puro (sin dependencias nuevas como Shapely).

Se usan para determinar automaticamente en que ZonaGeografica cae un punto
(lat, lon) segun el poligono aproximado guardado en `ZonaGeografica.poligono`.
"""
from typing import Iterable, List, Optional, Sequence


def punto_en_poligono(lat: float, lon: float, poligono: Sequence[Sequence[float]]) -> bool:
    """
    Algoritmo de ray casting (incremento par-impar) para determinar si el punto
    (lat, lon) esta dentro de un poligono simple (sin auto-interseccion).

    `poligono` es una lista de vertices [lat, lon] (en ese orden, igual que en
    el modelo de datos). El poligono se considera cerrado implicitamente
    (el ultimo vertice se conecta con el primero).

    Complejidad O(n) sobre el numero de vertices. No requiere librerias
    geoespaciales externas.
    """
    if not poligono or len(poligono) < 3:
        return False

    dentro = False
    n = len(poligono)
    lat_j, lon_j = poligono[n - 1][0], poligono[n - 1][1]
    for i in range(n):
        lat_i, lon_i = poligono[i][0], poligono[i][1]
        # Se evalua el cruce del rayo horizontal (a longitud constante `lon`)
        # contra cada arista del poligono.
        interseca = ((lon_i > lon) != (lon_j > lon)) and (
            lat < (lat_j - lat_i) * (lon - lon_i) / ((lon_j - lon_i) or 1e-15) + lat_i
        )
        if interseca:
            dentro = not dentro
        lat_j, lon_j = lat_i, lon_i
    return dentro


def determinar_zona(lat: float, lon: float, zonas: Iterable) -> Optional[object]:
    """
    Recorre las zonas geograficas disponibles (objetos con atributos
    `.poligono` y `.id`/`.nombre`) y retorna la primera cuyo poligono
    contenga el punto (lat, lon). Si ninguna lo contiene, retorna None
    (el llamador debe aplicar su propio respaldo, ej. el zona_geografica_id
    manual del cliente).

    Si dos poligonos llegaran a solaparse (no deberia ocurrir con los
    poligonos aproximados construidos para v2, verificado en pruebas), se
    retorna la primera coincidencia en el orden recibido.
    """
    for zona in zonas:
        poligono = getattr(zona, "poligono", None)
        if not poligono:
            continue
        if punto_en_poligono(lat, lon, poligono):
            return zona
    return None
