"""
Agrega datos de prueba mas ricos a "Empresa Demo 2" (la empresa de prueba que
crea migrate_v4_backfill.py con solo 1 CEDI, 2 clientes, 1 transportista y 1
ruta) -- pensado para que el Mapa de Rutas, el Mapa General y la Conciliacion
tengan contenido real que mostrar al probar el aislamiento por empresa.

Requiere que "Empresa Demo 2" ya exista (creada por migrate_v4_backfill.py).
Es idempotente (usa get-or-create por nombre/codigo): se puede correr varias
veces sin duplicar nada.

Agrega: 1 CEDI adicional (2 en total), 2 zonas geograficas adicionales con
poligono (3 en total, y le agrega poligono a la zona existente si no tenia),
1 tipo de cliente adicional, 2 tipos de camion adicionales, 8 clientes
adicionales en zonas Sur/Norte/Centro de Medellin, 2 transportistas
adicionales con tarifas de varios metodos (POR_PARADA, POR_ZONA,
POR_KILOMETRO, POR_PESO_VOLUMEN), 3 productos adicionales, y 4 pares de rutas
planificada/ejecutada con diferencias deliberadas (para que Conciliacion
muestre algo interesante).

Uso local (docker compose):
    docker compose exec backend python seed_empresa_demo_2.py

Uso contra produccion en Render (mismo patron que los otros scripts de backfill):
    docker run -it --rm \
      -e DATABASE_URL="<tu External Database URL>/flete_db" \
      -v "$(pwd)/backend:/app" -w /app python:3.11-slim \
      bash -c "pip install -q -r requirements.txt && python seed_empresa_demo_2.py"
"""
import sys
from datetime import datetime

from app.database import SessionLocal
from app.models import models
from app.services.flete_calculo import calcular_y_guardar
from app.services.distance_connector import calcular_distancia_tiempo
from app.services.geo import punto_en_poligono


def _get_or_create(db, modelo, filtro: dict, defaults: dict):
    obj = db.query(modelo).filter_by(**filtro).first()
    if obj:
        return obj, False
    obj = modelo(**filtro, **defaults)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj, True


def _crear_ruta(db, empresa_id, codigo_ruta, es_planificada, ruta_planificada_id, centro, transportista,
                tarifa, tipo_camion, fecha, paradas_spec):
    """paradas_spec: lista de dicts {cliente, secuencia, distancia_km_tramo,
    tiempo_transito_min_tramo, tiempo_servicio_min, pedidos: [(producto, cantidad), ...]}

    Ademas de lo "importado" (distancia_km_tramo/tiempo_transito_min_tramo, que
    aqui se fija a mano para simular datos de un archivo real), calcula SIEMPRE
    el dato de referencia (Google/Haversine, igual que hace el import real en
    rutas.py) para que el detalle de calculo tenga con que comparar -- si no,
    el bloque de comparacion queda con ceros/valores enganosos."""
    existente = (
        db.query(models.Ruta)
        .filter(models.Ruta.empresa_id == empresa_id, models.Ruta.codigo_ruta == codigo_ruta,
                models.Ruta.es_planificada == es_planificada)
        .first()
    )
    if existente:
        print(f"    {codigo_ruta} ({'plan' if es_planificada else 'ejec'}): ya existia (id {existente.id})")
        return existente

    ruta = models.Ruta(
        empresa_id=empresa_id, codigo_ruta=codigo_ruta, es_planificada=es_planificada,
        ruta_planificada_id=ruta_planificada_id, centro_distribucion_id=centro.id,
        transportista_id=transportista.id, tarifa_transportista_id=tarifa.id,
        tipo_camion_id=tipo_camion.id, fecha=fecha,
        estado="PLANIFICADA" if es_planificada else "EJECUTADA",
    )
    db.add(ruta)
    db.flush()
    punto_anterior = (centro.latitud, centro.longitud)
    for p in paradas_spec:
        cliente = p["cliente"]
        referencia = calcular_distancia_tiempo(
            punto_anterior[0], punto_anterior[1], cliente.latitud, cliente.longitud
        )
        parada = models.ParadaRuta(
            ruta_id=ruta.id, cliente_id=cliente.id, secuencia=p["secuencia"],
            distancia_km_tramo=p.get("distancia_km_tramo", 5.0),
            tiempo_transito_min_tramo=p.get("tiempo_transito_min_tramo", 12),
            distancia_km_tramo_referencia=referencia.distancia_km,
            tiempo_transito_min_tramo_referencia=referencia.tiempo_min,
            fuente_referencia=referencia.fuente,
            tiempo_servicio_min=p.get("tiempo_servicio_min", 15),
        )
        punto_anterior = (cliente.latitud, cliente.longitud)
        db.add(parada)
        db.flush()
        for producto, cantidad in p.get("pedidos", []):
            db.add(
                models.PedidoClienteRuta(
                    parada_ruta_id=parada.id, producto_id=producto.id, cantidad=cantidad,
                    peso_kg=producto.peso_unitario_kg * cantidad,
                    volumen_m3=producto.volumen_unitario_m3 * cantidad,
                )
            )
    db.commit()
    db.refresh(ruta)
    calcular_y_guardar(db, ruta)
    print(f"    {codigo_ruta} ({'plan' if es_planificada else 'ejec'}): creada (id {ruta.id}, costo {ruta.costo_flete_calculado})")
    return ruta


def main():
    db = SessionLocal()
    try:
        empresa2 = db.query(models.Empresa).filter(models.Empresa.nombre == "Empresa Demo 2").first()
        if not empresa2:
            print(
                "No existe 'Empresa Demo 2' todavia. Corre primero migrate_v4_backfill.py "
                "(crea la empresa base) antes de este script."
            )
            sys.exit(1)
        eid = empresa2.id
        print(f"Empresa Demo 2 detectada (id {eid}). Agregando datos adicionales...")

        # ---------- Zonas ----------
        # Rectangulos simples (no son limites administrativos oficiales, solo
        # aproximaciones para el demo) elegidos y VERIFICADOS con
        # punto_en_poligono contra las coordenadas de los clientes de abajo,
        # con margen y sin solaparse entre si, para que la deteccion
        # automatica de zona (punto-en-poligono, usada por el metodo POR_ZONA)
        # coincida siempre con la zona asignada manualmente al cliente.
        print("\n== Zonas geograficas ==")
        poligono_centro = [[6.26, -75.55], [6.26, -75.615], [6.195, -75.615], [6.195, -75.55]]
        poligono_sur = [[6.19, -75.58], [6.19, -75.625], [6.14, -75.625], [6.14, -75.58]]
        poligono_norte = [[6.35, -75.55], [6.35, -75.61], [6.26, -75.61], [6.26, -75.55]]

        zona_centro = db.query(models.ZonaGeografica).filter_by(empresa_id=eid, nombre="Zona Medellin Centro").first()
        if zona_centro:
            zona_centro.poligono = poligono_centro
            db.commit()
            print("  Zona Medellin Centro: poligono actualizado")

        zona_sur, creada = _get_or_create(
            db, models.ZonaGeografica, {"empresa_id": eid, "nombre": "Zona Medellin Sur"},
            {"descripcion": "Envigado, Sabaneta, Itagui", "tarifa_zona": 95000, "poligono": poligono_sur},
        )
        if not creada:
            zona_sur.poligono = poligono_sur
            db.commit()
        print(f"  Zona Medellin Sur: {'creada' if creada else 'ya existia (poligono actualizado)'} (id {zona_sur.id})")

        zona_norte, creada = _get_or_create(
            db, models.ZonaGeografica, {"empresa_id": eid, "nombre": "Zona Medellin Norte"},
            {"descripcion": "Bello, Robledo, Castilla", "tarifa_zona": 110000, "poligono": poligono_norte},
        )
        if not creada:
            zona_norte.poligono = poligono_norte
            db.commit()
        print(f"  Zona Medellin Norte: {'creada' if creada else 'ya existia (poligono actualizado)'} (id {zona_norte.id})")

        # ---------- CEDI adicional ----------
        print("\n== Centros de Distribucion ==")
        cedi_sur, creada = _get_or_create(
            db, models.CentroDistribucion, {"empresa_id": eid, "codigo": "CEDI-MED-SUR"},
            {"nombre": "CEDI Medellin Sur", "latitud": 6.1729, "longitud": -75.5910, "direccion": "Envigado, Medellin"},
        )
        cedi_centro = db.query(models.CentroDistribucion).filter_by(empresa_id=eid, codigo="CEDI-MED").first()
        print(f"  CEDI Medellin Sur: {'creado' if creada else 'ya existia'} (id {cedi_sur.id})")

        # ---------- Tipos de cliente / camion ----------
        tipo_moderno, _ = _get_or_create(
            db, models.TipoCliente, {"empresa_id": eid, "nombre": "Moderno"},
            {"descripcion": "Supermercado / cadena"},
        )
        tipo_turbo, _ = _get_or_create(
            db, models.TipoCamion, {"empresa_id": eid, "nombre": "Turbo"},
            {"capacidad_peso_kg": 5000, "capacidad_volumen_m3": 20},
        )
        tipo_sencillo, _ = _get_or_create(
            db, models.TipoCamion, {"empresa_id": eid, "nombre": "Sencillo"},
            {"capacidad_peso_kg": 8000, "capacidad_volumen_m3": 35},
        )
        tipo_nhr = db.query(models.TipoCamion).filter_by(empresa_id=eid, nombre="NHR").first()
        tipo_general = db.query(models.TipoCliente).filter_by(empresa_id=eid, nombre="General").first()

        # ---------- Clientes adicionales ----------
        # Nota: "Exito Poblado" queda en Zona Centro (no Sur) -- a esa latitud
        # (6.2087) queda mas cerca del cluster centro que del cluster sur real
        # de Medellin, y asi coincide con el poligono de arriba (evita el caso
        # de un cliente cuya zona manual no coincide con la deteccion
        # automatica por punto-en-poligono, que confundia el calculo POR_ZONA).
        print("\n== Clientes ==")
        clientes_data = [
            ("CLI-D2-003", "Exito Poblado", 6.2087, -75.5679, zona_centro),
            ("CLI-D2-004", "Tienda Envigado Centro", 6.1729, -75.5910, zona_sur),
            ("CLI-D2-005", "Supermercado Sabaneta", 6.1518, -75.6165, zona_sur),
            ("CLI-D2-006", "Minimarket Itagui", 6.1719, -75.6122, zona_sur),
            ("CLI-D2-007", "Carulla Laureles", 6.2447, -75.5911, zona_centro),
            ("CLI-D2-008", "Tienda Belen", 6.2249, -75.6067, zona_centro),
            ("CLI-D2-009", "D1 Bello", 6.3373, -75.5580, zona_norte),
            ("CLI-D2-010", "Ara Robledo", 6.2789, -75.5959, zona_norte),
        ]
        clientes = {}
        c1 = db.query(models.Cliente).filter_by(empresa_id=eid, codigo="CLI-D2-001").first()
        c2 = db.query(models.Cliente).filter_by(empresa_id=eid, codigo="CLI-D2-002").first()
        clientes["CLI-D2-001"] = c1
        clientes["CLI-D2-002"] = c2
        for codigo, nombre, lat, lon, zona in clientes_data:
            cli, creada = _get_or_create(
                db, models.Cliente, {"empresa_id": eid, "codigo": codigo},
                {
                    "tipo_cliente_id": tipo_moderno.id, "zona_geografica_id": zona.id,
                    "nombre": nombre, "latitud": lat, "longitud": lon,
                    "direccion": f"{nombre}, Medellin", "canal": "Moderno",
                },
            )
            if not creada and cli.zona_geografica_id != zona.id:
                cli.zona_geografica_id = zona.id
                db.commit()
                print(f"  {nombre}: zona corregida a {zona.nombre}")
            clientes[codigo] = cli
            print(f"  {nombre}: {'creado' if creada else 'ya existia'}")

        # Verificacion: confirma que la deteccion automatica por punto-en-poligono
        # coincide con la zona asignada manualmente a cada cliente, para todos
        # los clientes de Empresa Demo 2 (evita que el metodo POR_ZONA de una
        # zona distinta a la esperada, como paso con la version anterior de
        # este script).
        print("\n== Verificacion de zonas (punto-en-poligono) ==")
        todas_zonas = db.query(models.ZonaGeografica).filter_by(empresa_id=eid).all()
        todos_clientes = db.query(models.Cliente).filter_by(empresa_id=eid).all()
        for cli in todos_clientes:
            zona_manual = next((z for z in todas_zonas if z.id == cli.zona_geografica_id), None)
            zona_detectada = next(
                (z for z in todas_zonas if z.poligono and punto_en_poligono(cli.latitud, cli.longitud, z.poligono)),
                None,
            )
            ok = zona_detectada is not None and zona_manual is not None and zona_detectada.id == zona_manual.id
            estado = "OK" if ok else "DESAJUSTE"
            print(f"  [{estado}] {cli.nombre}: manual={zona_manual.nombre if zona_manual else '-'} detectada={zona_detectada.nombre if zona_detectada else '-'}")

        # ---------- Productos adicionales ----------
        print("\n== Productos ==")
        prod_demo = db.query(models.Producto).filter_by(empresa_id=eid, codigo="DEMO-001").first()
        productos_data = [
            ("DEMO-002", "Aceite Vegetal 1L", 1.0, 0.0012),
            ("DEMO-003", "Detergente 3kg", 3.0, 0.0035),
            ("DEMO-004", "Gaseosa 1.5L", 9.0, 0.01),
        ]
        productos = {"DEMO-001": prod_demo}
        for codigo, nombre, peso, vol in productos_data:
            prod, creada = _get_or_create(
                db, models.Producto, {"empresa_id": eid, "codigo": codigo},
                {"nombre": nombre, "peso_unitario_kg": peso, "volumen_unitario_m3": vol},
            )
            productos[codigo] = prod
            print(f"  {nombre}: {'creado' if creada else 'ya existia'}")

        # ---------- Transportistas adicionales ----------
        print("\n== Transportistas y tarifas ==")
        trans_demo2 = db.query(models.Transportista).filter_by(empresa_id=eid, nit="900777666-1").first()
        rapiflete, _ = _get_or_create(
            db, models.Transportista, {"empresa_id": eid, "nit": "900888777-2"},
            {"nombre": "Rapiflete Antioquia", "contacto": "Contacto Rapiflete", "telefono": "300-111-2222"},
        )
        logimed, _ = _get_or_create(
            db, models.Transportista, {"empresa_id": eid, "nit": "900666555-3"},
            {"nombre": "LogiMed", "contacto": "Contacto LogiMed", "telefono": "300-333-4444"},
        )

        metodos = {
            m.codigo: m for m in db.query(models.MetodoTarifa).filter_by(empresa_id=eid).all()
        }

        tarifa_parada, _ = _get_or_create(
            db, models.TarifaTransportista,
            {"empresa_id": eid, "transportista_id": trans_demo2.id, "metodo_tarifa_id": metodos["POR_PARADA"].id},
            {"tipo_camion_id": None, "nombre": "Tarifa por parada - Demo 2", "valor_unitario": 15000, "unidad": "PARADA", "activo": True},
        )
        tarifa_zona, creada = _get_or_create(
            db, models.TarifaTransportista,
            {"empresa_id": eid, "transportista_id": rapiflete.id, "metodo_tarifa_id": metodos["POR_ZONA"].id},
            {"tipo_camion_id": None, "nombre": "Tarifa por zona - Rapiflete", "valor_unitario": 0, "unidad": "ZONA", "activo": True},
        )
        if creada:
            db.add_all([
                models.TarifaZonaDetalle(tarifa_transportista_id=tarifa_zona.id, zona_geografica_id=zona_centro.id, valor=85000),
                models.TarifaZonaDetalle(tarifa_transportista_id=tarifa_zona.id, zona_geografica_id=zona_sur.id, valor=95000),
                models.TarifaZonaDetalle(tarifa_transportista_id=tarifa_zona.id, zona_geografica_id=zona_norte.id, valor=110000),
            ])
            db.commit()
        tarifa_km, _ = _get_or_create(
            db, models.TarifaTransportista,
            {"empresa_id": eid, "transportista_id": rapiflete.id, "metodo_tarifa_id": metodos["POR_KILOMETRO"].id},
            {"tipo_camion_id": None, "nombre": "Tarifa por km - Rapiflete", "valor_unitario": 2500, "unidad": "KM", "activo": True},
        )
        tarifa_peso, _ = _get_or_create(
            db, models.TarifaTransportista,
            {"empresa_id": eid, "transportista_id": logimed.id, "metodo_tarifa_id": metodos["POR_PESO_VOLUMEN"].id},
            {"tipo_camion_id": None, "nombre": "Tarifa por kg - LogiMed", "valor_unitario": 800, "unidad": "KG", "activo": True},
        )
        print("  Tarifas POR_PARADA/POR_ZONA/POR_KILOMETRO/POR_PESO_VOLUMEN listas")

        # ---------- Rutas planificada/ejecutada ----------
        print("\n== Rutas (planificada + ejecutada) ==")

        print("  RUTA-DEMO2-002 (Transportes Demo 2, POR_PARADA, CEDI Centro)")
        rp2 = _crear_ruta(
            db, eid, "RUTA-DEMO2-002", True, None, cedi_centro, trans_demo2, tarifa_parada, tipo_turbo,
            datetime(2026, 7, 1, 8, 0, 0),
            [
                {"cliente": clientes["CLI-D2-007"], "secuencia": 1, "distancia_km_tramo": 3.5, "tiempo_transito_min_tramo": 10, "tiempo_servicio_min": 15, "pedidos": [(productos["DEMO-002"], 30)]},
                {"cliente": clientes["CLI-D2-008"], "secuencia": 2, "distancia_km_tramo": 4.2, "tiempo_transito_min_tramo": 12, "tiempo_servicio_min": 15, "pedidos": [(productos["DEMO-002"], 25)]},
            ],
        )
        _crear_ruta(
            db, eid, "RUTA-DEMO2-002", False, rp2.id, cedi_centro, trans_demo2, tarifa_parada, tipo_turbo,
            datetime(2026, 7, 1, 8, 0, 0),
            [
                {"cliente": clientes["CLI-D2-007"], "secuencia": 1, "distancia_km_tramo": 3.8, "tiempo_transito_min_tramo": 14, "tiempo_servicio_min": 18, "pedidos": [(productos["DEMO-002"], 30)]},
                {"cliente": clientes["CLI-D2-008"], "secuencia": 2, "distancia_km_tramo": 4.5, "tiempo_transito_min_tramo": 15, "tiempo_servicio_min": 15, "pedidos": [(productos["DEMO-002"], 25)]},
                {"cliente": clientes["CLI-D2-001"], "secuencia": 3, "distancia_km_tramo": 6.0, "tiempo_transito_min_tramo": 20, "tiempo_servicio_min": 20, "pedidos": [(productos["DEMO-001"], 10)]},
            ],
        )

        print("  RUTA-DEMO2-003 (Rapiflete, POR_ZONA, CEDI Sur -- desvio a zona mas cara en ejecucion)")
        rp3 = _crear_ruta(
            db, eid, "RUTA-DEMO2-003", True, None, cedi_sur, rapiflete, tarifa_zona, tipo_sencillo,
            datetime(2026, 7, 2, 7, 0, 0),
            [
                {"cliente": clientes["CLI-D2-003"], "secuencia": 1, "distancia_km_tramo": 4.0, "tiempo_transito_min_tramo": 10, "tiempo_servicio_min": 20, "pedidos": [(productos["DEMO-003"], 15)]},
                {"cliente": clientes["CLI-D2-004"], "secuencia": 2, "distancia_km_tramo": 3.0, "tiempo_transito_min_tramo": 8, "tiempo_servicio_min": 20, "pedidos": [(productos["DEMO-003"], 15)]},
            ],
        )
        _crear_ruta(
            db, eid, "RUTA-DEMO2-003", False, rp3.id, cedi_sur, rapiflete, tarifa_zona, tipo_sencillo,
            datetime(2026, 7, 2, 7, 0, 0),
            [
                {"cliente": clientes["CLI-D2-003"], "secuencia": 1, "distancia_km_tramo": 4.2, "tiempo_transito_min_tramo": 11, "tiempo_servicio_min": 22, "pedidos": [(productos["DEMO-003"], 15)]},
                {"cliente": clientes["CLI-D2-004"], "secuencia": 2, "distancia_km_tramo": 3.1, "tiempo_transito_min_tramo": 9, "tiempo_servicio_min": 20, "pedidos": [(productos["DEMO-003"], 15)]},
                {"cliente": clientes["CLI-D2-009"], "secuencia": 3, "distancia_km_tramo": 22.0, "tiempo_transito_min_tramo": 45, "tiempo_servicio_min": 20, "pedidos": [(productos["DEMO-004"], 20)]},
            ],
        )

        print("  RUTA-DEMO2-004 (Rapiflete, POR_KILOMETRO, CEDI Centro -- recorrido real mas largo)")
        rp4 = _crear_ruta(
            db, eid, "RUTA-DEMO2-004", True, None, cedi_centro, rapiflete, tarifa_km, tipo_sencillo,
            datetime(2026, 7, 3, 7, 30, 0),
            [
                {"cliente": clientes["CLI-D2-009"], "secuencia": 1, "distancia_km_tramo": 9.5, "tiempo_transito_min_tramo": 22, "tiempo_servicio_min": 20, "pedidos": [(productos["DEMO-001"], 20)]},
                {"cliente": clientes["CLI-D2-010"], "secuencia": 2, "distancia_km_tramo": 5.2, "tiempo_transito_min_tramo": 14, "tiempo_servicio_min": 20, "pedidos": [(productos["DEMO-001"], 20)]},
            ],
        )
        _crear_ruta(
            db, eid, "RUTA-DEMO2-004", False, rp4.id, cedi_centro, rapiflete, tarifa_km, tipo_sencillo,
            datetime(2026, 7, 3, 7, 30, 0),
            [
                {"cliente": clientes["CLI-D2-009"], "secuencia": 1, "distancia_km_tramo": 11.8, "tiempo_transito_min_tramo": 30, "tiempo_servicio_min": 22, "pedidos": [(productos["DEMO-001"], 20)]},
                {"cliente": clientes["CLI-D2-010"], "secuencia": 2, "distancia_km_tramo": 6.9, "tiempo_transito_min_tramo": 19, "tiempo_servicio_min": 20, "pedidos": [(productos["DEMO-001"], 20)]},
            ],
        )

        print("  RUTA-DEMO2-005 (LogiMed, POR_PESO_VOLUMEN, CEDI Sur -- mas peso entregado en ejecucion)")
        rp5 = _crear_ruta(
            db, eid, "RUTA-DEMO2-005", True, None, cedi_sur, logimed, tarifa_peso, tipo_nhr,
            datetime(2026, 7, 4, 8, 0, 0),
            [
                {"cliente": clientes["CLI-D2-005"], "secuencia": 1, "distancia_km_tramo": 6.5, "tiempo_transito_min_tramo": 16, "tiempo_servicio_min": 18, "pedidos": [(productos["DEMO-002"], 40), (productos["DEMO-004"], 15)]},
                {"cliente": clientes["CLI-D2-006"], "secuencia": 2, "distancia_km_tramo": 4.0, "tiempo_transito_min_tramo": 11, "tiempo_servicio_min": 18, "pedidos": [(productos["DEMO-002"], 35)]},
            ],
        )
        _crear_ruta(
            db, eid, "RUTA-DEMO2-005", False, rp5.id, cedi_sur, logimed, tarifa_peso, tipo_nhr,
            datetime(2026, 7, 4, 8, 0, 0),
            [
                {"cliente": clientes["CLI-D2-005"], "secuencia": 1, "distancia_km_tramo": 6.7, "tiempo_transito_min_tramo": 17, "tiempo_servicio_min": 20, "pedidos": [(productos["DEMO-002"], 48), (productos["DEMO-004"], 15)]},
                {"cliente": clientes["CLI-D2-006"], "secuencia": 2, "distancia_km_tramo": 4.1, "tiempo_transito_min_tramo": 12, "tiempo_servicio_min": 18, "pedidos": [(productos["DEMO-002"], 35)]},
            ],
        )

        print("\nSEED DE EMPRESA DEMO 2 COMPLETADO.")
        print(
            f"Resumen: 2 CEDIs, 3 zonas, {2 + len(clientes_data)} clientes, 3 tipos de camion, "
            f"3 transportistas, {1 + len(productos_data)} productos, 5 pares de rutas planificada/ejecutada."
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
