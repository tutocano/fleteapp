"""
Script de una sola vez para "rellenar" en paradas de rutas YA EXISTENTES (creadas
antes de v3, cuando distancia_km_tramo_referencia/tiempo_transito_min_tramo_referencia
no existian) los nuevos campos de distancia/tiempo de REFERENCIA (Google Routes API o
Haversine, ver app/services/distance_connector.py).

No vuelve a importar ninguna ruta y NUNCA toca distancia_km_tramo/tiempo_transito_min_tramo
(los valores originalmente importados quedan intactos) -- solo llena los campos
"_referencia" que esten vacios, y despues recalcula y guarda detalle_calculo de cada
ruta afectada para que el bloque "comparacion_distancia_tiempo" quede persistido (si no,
solo apareceria calculando de nuevo, y GET /rutas/{id} devuelve el detalle ya guardado).

Es idempotente: si se corre varias veces, la segunda vez no hace nada (todas las
paradas ya tienen su dato de referencia). Usa --force si se quiere recalcular TODAS
las paradas de nuevo, por ejemplo porque se agrego GOOGLE_MAPS_API_KEY despues de que
ya se habian llenado con el fallback de Haversine y se quiere reintentar con Google.

Uso local (con la BD del docker-compose):
    docker compose exec backend python backfill_distancia_referencia.py
    docker compose exec backend python backfill_distancia_referencia.py --force

Uso contra la base de datos de produccion en Render (igual que se corrio seed.py,
ver GUIA_DESPLIEGUE_RENDER.md): desde tu Mac, con Docker corriendo,

    docker run -it --rm \
      -e DATABASE_URL="<tu connection string de Postgres + /flete_db>" \
      -e GOOGLE_MAPS_API_KEY="<tu key, opcional>" \
      -v "$(pwd)/backend:/app" -w /app python:3.11-slim \
      bash -c "pip install -q -r requirements.txt && python backfill_distancia_referencia.py"
"""
import sys

from app.database import SessionLocal
from app.models import models
from app.services.distance_connector import calcular_distancia_tiempo
from app.services.flete_calculo import calcular_y_guardar


def main():
    force = "--force" in sys.argv
    db = SessionLocal()
    try:
        rutas = db.query(models.Ruta).all()
        print(f"{len(rutas)} rutas encontradas en la base de datos.")
        if force:
            print("Modo --force: se recalculan TODAS las paradas, incluso las que ya tenian referencia.")

        rutas_afectadas = 0
        paradas_actualizadas = 0

        for ruta in rutas:
            paradas = sorted(ruta.paradas, key=lambda p: p.secuencia)
            if not paradas:
                continue

            punto_anterior = (ruta.centro_distribucion.latitud, ruta.centro_distribucion.longitud)
            cambio_en_ruta = False

            for parada in paradas:
                cliente = parada.cliente
                if parada.distancia_km_tramo_referencia is not None and not force:
                    punto_anterior = (cliente.latitud, cliente.longitud)
                    continue

                resultado = calcular_distancia_tiempo(
                    punto_anterior[0], punto_anterior[1], cliente.latitud, cliente.longitud
                )
                parada.distancia_km_tramo_referencia = resultado.distancia_km
                parada.tiempo_transito_min_tramo_referencia = resultado.tiempo_min
                parada.fuente_referencia = resultado.fuente
                paradas_actualizadas += 1
                cambio_en_ruta = True
                punto_anterior = (cliente.latitud, cliente.longitud)

            if cambio_en_ruta:
                rutas_afectadas += 1
                # calcular_y_guardar hace commit() y refresh() internamente: persiste
                # tanto las paradas modificadas de arriba como el detalle_calculo nuevo
                # (con el bloque comparacion_distancia_tiempo) en la misma transaccion.
                calcular_y_guardar(db, ruta)
                print(f"  Ruta {ruta.id} ({ruta.codigo_ruta}): actualizada.")

        print(f"\nListo. {paradas_actualizadas} paradas actualizadas en {rutas_afectadas} rutas.")
        if rutas_afectadas == 0:
            print("(Todas las rutas ya tenian datos de referencia; usa --force para recalcular igual.)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
