"""
Script de datos semilla para Fleteapp.

Puede ejecutarse:
  - Dentro del contenedor backend: `python seed.py` (usa BASE_URL=http://localhost:8000/api por defecto)
  - Desde el host contra el backend expuesto: `BASE_URL=http://localhost:8000/api python seed.py`

Crea: 1 empresa, 2 CEDIs, tipos de cliente, ~15 clientes (Bogota), 3 tipos de camion,
3 transportistas con tarifas cubriendo los 5 metodos, zonas geograficas, 5-8 productos,
y una ruta planificada + su ruta ejecutada (con diferencias deliberadas) para demostrar
la conciliacion.
"""
import os
import sys
import time
import httpx

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000/api")


def wait_for_api(max_tries=30):
    for i in range(max_tries):
        try:
            r = httpx.get(BASE_URL.replace("/api", "/health"), timeout=3.0, trust_env=False)
            if r.status_code == 200:
                print("API disponible.")
                return
        except Exception:
            pass
        print(f"Esperando API... intento {i+1}/{max_tries}")
        time.sleep(2)
    print("ERROR: la API no respondio a tiempo.")
    sys.exit(1)


def post(path, payload):
    r = httpx.post(f"{BASE_URL}{path}", json=payload, timeout=15.0, trust_env=False)
    if r.status_code >= 300:
        print(f"ERROR POST {path}: {r.status_code} {r.text}")
        r.raise_for_status()
    return r.json()


def get(path):
    r = httpx.get(f"{BASE_URL}{path}", timeout=15.0, trust_env=False)
    r.raise_for_status()
    return r.json()


def main():
    wait_for_api()

    print("\n== Empresa ==")
    empresa = post(
        "/empresas/",
        {
            "nombre": "Distribuidora ConsumoMasivo S.A.S.",
            "nit": "900123456-7",
            "direccion": "Cra 45 # 26-20, Bogota",
            "telefono": "601-555-1234",
            "email": "operaciones@consumomasivo.co",
        },
    )
    empresa_id = empresa["id"]
    print("Empresa creada:", empresa_id)

    print("\n== Centros de Distribucion ==")
    cedi_norte = post(
        "/centros-distribucion/",
        {
            "empresa_id": empresa_id,
            "nombre": "CEDI Bogota Norte",
            "codigo": "CEDI-NORTE",
            "latitud": 4.7589,
            "longitud": -74.0453,
            "direccion": "Autopista Norte # 190-30, Bogota",
        },
    )
    cedi_sur = post(
        "/centros-distribucion/",
        {
            "empresa_id": empresa_id,
            "nombre": "CEDI Bogota Sur",
            "codigo": "CEDI-SUR",
            "latitud": 4.5709,
            "longitud": -74.1234,
            "direccion": "Autopista Sur # 60-15, Bogota",
        },
    )
    print("CEDIs creados:", cedi_norte["id"], cedi_sur["id"])

    print("\n== Tipos de Cliente ==")
    tipo_tradicional = post("/tipos-cliente/", {"nombre": "Tradicional", "descripcion": "Tienda de barrio"})
    tipo_moderno = post("/tipos-cliente/", {"nombre": "Moderno", "descripcion": "Supermercado / cadena"})
    tipo_mayorista = post("/tipos-cliente/", {"nombre": "Mayorista", "descripcion": "Distribuidor mayorista"})
    print("Tipos de cliente creados")

    print("\n== Zonas Geograficas ==")
    # NOTA v2: los poligonos abajo son aproximados, construidos manualmente a partir
    # del conocimiento general de la geografia/localidades de Bogota (8-12 vertices
    # cada uno, sin auto-interseccion). NO son un shapefile oficial. Se verifico que
    # los 15 clientes de este seed y los 2 CEDIs caen dentro de alguna de estas 4
    # zonas y que los poligonos no se solapan entre si (script de verificacion en
    # el flujo de build de v2). En el futuro pueden reemplazarse por el GeoJSON
    # oficial de localidades de IDECA (https://www.ideca.gov.co/) sin cambiar el
    # modelo de datos: basta con sobreescribir el campo `poligono`.
    poligono_centro = [
        [4.6720, -74.0700], [4.6650, -74.0560], [4.6450, -74.0500], [4.6250, -74.0560],
        [4.6050, -74.0680], [4.5980, -74.0900], [4.6150, -74.1020], [4.6450, -74.0980],
        [4.6650, -74.0900],
    ]
    poligono_norte = [
        [4.6720, -74.0700], [4.6650, -74.0900], [4.6700, -74.1150], [4.6950, -74.1300],
        [4.7550, -74.1200], [4.8150, -74.0700], [4.8000, -74.0100], [4.7300, -74.0050],
        [4.6900, -74.0250], [4.6650, -74.0560],
    ]
    poligono_sur = [
        [4.6150, -74.1020], [4.5980, -74.0900], [4.6050, -74.0680], [4.6250, -74.0560],
        [4.6100, -74.0520], [4.5750, -74.0650], [4.5300, -74.0850], [4.5050, -74.1300],
        [4.5350, -74.1650], [4.5900, -74.1650], [4.6350, -74.1650], [4.6450, -74.1300],
    ]
    poligono_occidente = [
        [4.6950, -74.1300], [4.6700, -74.1150], [4.6450, -74.1300], [4.6350, -74.1650],
        [4.5900, -74.1650], [4.5350, -74.1650], [4.5050, -74.1950], [4.5350, -74.2500],
        [4.6000, -74.2550], [4.6600, -74.2100], [4.7000, -74.1700],
    ]
    zona_centro = post(
        "/zonas-geograficas/",
        {"nombre": "Zona Centro", "descripcion": "Centro de Bogota (Chapinero centro, Santa Fe, Candelaria, Paloquemao)",
         "tarifa_zona": 80000, "poligono": poligono_centro},
    )
    zona_norte = post(
        "/zonas-geograficas/",
        {"nombre": "Zona Norte", "descripcion": "Norte de Bogota (Usaquen, Suba oriental, Chapinero norte)",
         "tarifa_zona": 100000, "poligono": poligono_norte},
    )
    zona_sur = post(
        "/zonas-geograficas/",
        {"nombre": "Zona Sur", "descripcion": "Sur de Bogota (Kennedy, Tunjuelito, Restrepo)",
         "tarifa_zona": 90000, "poligono": poligono_sur},
    )
    zona_occidente = post(
        "/zonas-geograficas/",
        {"nombre": "Zona Occidente/Soacha", "descripcion": "Occidente y Soacha (Bosa, Fontibon, limite con Soacha, la mas alejada)",
         "tarifa_zona": 150000, "poligono": poligono_occidente},
    )
    print("Zonas creadas (con poligonos aproximados v2)")

    print("\n== Clientes (Bogota) ==")
    # 15 clientes con coordenadas reales aproximadas de Bogota, distribuidos por zona/canal
    clientes_data = [
        ("Super Exito Chapinero", 4.6467, -74.0631, tipo_moderno, zona_centro, "Moderno"),
        ("Tienda Don Jose - Chapinero", 4.6389, -74.0625, tipo_tradicional, zona_centro, "Tradicional"),
        ("Carulla 85", 4.6685, -74.0548, tipo_moderno, zona_norte, "Moderno"),
        ("Ara Usaquen", 4.6959, -74.0308, tipo_moderno, zona_norte, "Moderno"),
        ("Tienda La Esquina - Usaquen", 4.6942, -74.0300, tipo_tradicional, zona_norte, "Tradicional"),
        ("Mayorista Corabastos", 4.6186, -74.1541, tipo_mayorista, zona_sur, "Mayorista"),
        ("Supermercado Kennedy", 4.6280, -74.1531, tipo_moderno, zona_sur, "Moderno"),
        ("Tienda El Progreso - Bosa", 4.6083, -74.1776, tipo_tradicional, zona_occidente, "Tradicional"),
        ("Minimarket Soacha Centro", 4.5794, -74.2166, tipo_tradicional, zona_occidente, "Tradicional"),
        ("D1 Fontibon", 4.6728, -74.1466, tipo_moderno, zona_occidente, "Moderno"),
        ("Justo y Bueno Engativa", 4.7110, -74.1156, tipo_moderno, zona_norte, "Moderno"),
        ("Tienda Dona Maria - Suba", 4.7420, -74.0836, tipo_tradicional, zona_norte, "Tradicional"),
        ("Mayorista Paloquemao", 4.6155, -74.0847, tipo_mayorista, zona_centro, "Mayorista"),
        ("Alkosto Calle 80", 4.6919, -74.0765, tipo_moderno, zona_norte, "Moderno"),
        ("Tienda San Jorge - Restrepo", 4.5772, -74.1093, tipo_tradicional, zona_sur, "Tradicional"),
    ]
    clientes = []
    for nombre, lat, lon, tipo, zona, canal in clientes_data:
        c = post(
            "/clientes/",
            {
                "empresa_id": empresa_id,
                "tipo_cliente_id": tipo["id"],
                "zona_geografica_id": zona["id"],
                "nombre": nombre,
                "codigo": f"CLI-{len(clientes)+1:03d}",
                "latitud": lat,
                "longitud": lon,
                "direccion": f"{nombre}, Bogota",
                "canal": canal,
            },
        )
        clientes.append(c)
    print(f"{len(clientes)} clientes creados")

    print("\n== Tipos de Camion ==")
    tipo_nhr = post("/tipos-camion/", {"nombre": "NHR", "capacidad_peso_kg": 2500, "capacidad_volumen_m3": 12})
    tipo_turbo = post("/tipos-camion/", {"nombre": "Turbo", "capacidad_peso_kg": 5000, "capacidad_volumen_m3": 20})
    tipo_sencillo = post("/tipos-camion/", {"nombre": "Sencillo", "capacidad_peso_kg": 8000, "capacidad_volumen_m3": 35})
    print("Tipos de camion creados")

    print("\n== Productos ==")
    productos_data = [
        ("Aceite Vegetal 1L", "PROD-001", 1.0, 0.0012),
        ("Arroz Premium 500g", "PROD-002", 0.5, 0.0006),
        ("Detergente en Polvo 3kg", "PROD-003", 3.0, 0.0035),
        ("Gaseosa 1.5L (six pack)", "PROD-004", 9.0, 0.01),
        ("Jabon de Tocador (pack x12)", "PROD-005", 1.2, 0.0015),
        ("Cafe Molido 250g", "PROD-006", 0.25, 0.0004),
        ("Pasta Alimenticia 500g", "PROD-007", 0.5, 0.0007),
        ("Papel Higienico (pack x12)", "PROD-008", 2.0, 0.02),
    ]
    productos = []
    for nombre, codigo, peso, volumen in productos_data:
        p = post(
            "/productos/",
            {"nombre": nombre, "codigo": codigo, "peso_unitario_kg": peso, "volumen_unitario_m3": volumen},
        )
        productos.append(p)
    print(f"{len(productos)} productos creados")

    print("\n== Transportistas y Tarifas ==")
    # Transportista 1: TransRapido - ofrece POR_VIAJE y POR_PARADA
    trans1 = post(
        "/transportistas/",
        {"empresa_id": empresa_id, "nombre": "TransRapido S.A.S.", "nit": "800111222-1",
         "contacto": "Carlos Ramirez", "telefono": "310-111-2222"},
    )
    # Transportista 2: LogiCarga - ofrece POR_ZONA y POR_PESO_VOLUMEN
    trans2 = post(
        "/transportistas/",
        {"empresa_id": empresa_id, "nombre": "LogiCarga Ltda.", "nit": "800333444-2",
         "contacto": "Maria Fernandez", "telefono": "310-333-4444"},
    )
    # Transportista 3: Transportes del Valle - ofrece POR_TIEMPO_SERVICIO y POR_VIAJE
    trans3 = post(
        "/transportistas/",
        {"empresa_id": empresa_id, "nombre": "Transportes del Valle", "nit": "800555666-3",
         "contacto": "Jorge Salcedo", "telefono": "310-555-6666"},
    )

    metodos = {m["codigo"]: m for m in get("/metodos-tarifa/")}

    print("\n== Flota ==")
    post("/flota/", {"transportista_id": trans1["id"], "tipo_camion_id": tipo_turbo["id"], "placa": "TRA-101", "descripcion": "Turbo 1", "activo": True})
    post("/flota/", {"transportista_id": trans2["id"], "tipo_camion_id": tipo_sencillo["id"], "placa": "LOG-201", "descripcion": "Sencillo 1", "activo": True})
    post("/flota/", {"transportista_id": trans3["id"], "tipo_camion_id": tipo_nhr["id"], "placa": "VAL-301", "descripcion": "NHR 1", "activo": True})

    # Tarifa 1: TransRapido - Por viaje (general, aplica a cualquier tipo de camion
    # que no tenga una tarifa mas especifica definida abajo)
    tarifa_trans1_viaje = post(
        "/tarifas-transportista/",
        {
            "transportista_id": trans1["id"],
            "metodo_tarifa_id": metodos["POR_VIAJE"]["id"],
            "tipo_camion_id": None,
            "nombre": "Tarifa plana por viaje - TransRapido (cualquier camion)",
            "valor_unitario": 250000,
            "unidad": "VIAJE",
            "activo": True,
        },
    )
    # Tarifa 1b: TransRapido - Por viaje, pero restringida a camion NHR (mas
    # pequeno y barato de operar que el Turbo/Sencillo por defecto). Demuestra
    # que un mismo metodo puede tener valores distintos segun el tipo de camion:
    # esta tarifa SOLO puede usarse en rutas con tipo_camion_id = NHR.
    tarifa_trans1_viaje_nhr = post(
        "/tarifas-transportista/",
        {
            "transportista_id": trans1["id"],
            "metodo_tarifa_id": metodos["POR_VIAJE"]["id"],
            "tipo_camion_id": tipo_nhr["id"],
            "nombre": "Tarifa plana por viaje - TransRapido (solo camion NHR)",
            "valor_unitario": 180000,
            "unidad": "VIAJE",
            "activo": True,
        },
    )
    # Tarifa 2: TransRapido - Por parada
    tarifa_trans1_parada = post(
        "/tarifas-transportista/",
        {
            "transportista_id": trans1["id"],
            "metodo_tarifa_id": metodos["POR_PARADA"]["id"],
            "nombre": "Tarifa por parada - TransRapido",
            "valor_unitario": 15000,
            "unidad": "PARADA",
            "activo": True,
        },
    )
    # Tarifa 3: LogiCarga - Por zona (con tabla de zonas)
    tarifa_trans2_zona = post(
        "/tarifas-transportista/",
        {
            "transportista_id": trans2["id"],
            "metodo_tarifa_id": metodos["POR_ZONA"]["id"],
            "nombre": "Tarifa por zona - LogiCarga",
            "valor_unitario": 0,
            "unidad": "ZONA",
            "activo": True,
            "zonas_detalle": [
                {"zona_geografica_id": zona_centro["id"], "valor": 90000},
                {"zona_geografica_id": zona_norte["id"], "valor": 110000},
                {"zona_geografica_id": zona_sur["id"], "valor": 100000},
                {"zona_geografica_id": zona_occidente["id"], "valor": 180000},
            ],
        },
    )
    # Tarifa 4: LogiCarga - Por peso/volumen (kg)
    tarifa_trans2_peso = post(
        "/tarifas-transportista/",
        {
            "transportista_id": trans2["id"],
            "metodo_tarifa_id": metodos["POR_PESO_VOLUMEN"]["id"],
            "nombre": "Tarifa por kg entregado - LogiCarga",
            "valor_unitario": 800,
            "unidad": "KG",
            "activo": True,
        },
    )
    # Tarifa 5: Transportes del Valle - Por tiempo de servicio (minutos)
    tarifa_trans3_tiempo = post(
        "/tarifas-transportista/",
        {
            "transportista_id": trans3["id"],
            "metodo_tarifa_id": metodos["POR_TIEMPO_SERVICIO"]["id"],
            "nombre": "Tarifa por minuto de servicio - Transportes del Valle",
            "valor_unitario": 3500,
            "unidad": "MINUTO",
            "activo": True,
        },
    )
    # Tarifa 6: Transportes del Valle - Por viaje (segunda opcion)
    tarifa_trans3_viaje = post(
        "/tarifas-transportista/",
        {
            "transportista_id": trans3["id"],
            "metodo_tarifa_id": metodos["POR_VIAJE"]["id"],
            "nombre": "Tarifa plana por viaje - Transportes del Valle",
            "valor_unitario": 220000,
            "unidad": "VIAJE",
            "activo": True,
        },
    )
    # Tarifa 7 (v2): LogiCarga - Por kilometro recorrido
    tarifa_trans2_km = post(
        "/tarifas-transportista/",
        {
            "transportista_id": trans2["id"],
            "metodo_tarifa_id": metodos["POR_KILOMETRO"]["id"],
            "nombre": "Tarifa por km recorrido - LogiCarga",
            "valor_unitario": 2500,
            "unidad": "KM",
            "activo": True,
        },
    )
    print("Tarifas creadas para los 6 metodos, distribuidas en 3 transportistas")

    # ================= RUTA PLANIFICADA (usa metodo POR_ZONA, LogiCarga) =================
    print("\n== Ruta Planificada (LogiCarga, metodo POR_ZONA) ==")
    # Planificado: clientes en zonas Centro y Norte solamente. La mas cara planificada es Zona Norte = 110000
    seleccion_plan = [clientes[0], clientes[2], clientes[12], clientes[3]]
    # zonas: centro (Exito Chapinero), norte (Carulla 85), centro (Paloquemao), norte (Ara Usaquen)

    paradas_plan = []
    for i, cli in enumerate(seleccion_plan, start=1):
        paradas_plan.append(
            {
                "cliente_id": cli["id"],
                "secuencia": i,
                "tiempo_servicio_min": 20 + i * 2,  # variacion simple
                "pedidos": [
                    {"producto_id": productos[0]["id"], "cantidad": 50},
                    {"producto_id": productos[3]["id"], "cantidad": 20},
                ],
            }
        )

    ruta_plan = post(
        "/rutas/importar/planificada",
        {
            "codigo_ruta": "RUTA-BOG-001",
            "centro_distribucion_id": cedi_norte["id"],
            "transportista_id": trans2["id"],
            "tarifa_transportista_id": tarifa_trans2_zona["id"],
            "tipo_camion_id": tipo_sencillo["id"],
            "fecha": "2026-06-25T07:00:00",
            "paradas": paradas_plan,
        },
    )
    print("Ruta planificada creada. ID:", ruta_plan["id"], "| Costo estimado:", ruta_plan["costo_flete_calculado"])
    print("Explicacion:", ruta_plan["detalle_calculo"]["explicacion"])

    # ================= RUTA EJECUTADA (con desvio real: se agrego un cliente en zona mas cara) =================
    print("\n== Ruta Ejecutada (con diferencias reales) ==")
    # En la ejecucion real se atendio un cliente adicional no planificado en Zona Occidente (mas cara),
    # ademas de diferencias de peso entregado y tiempo de servicio en otras paradas.
    seleccion_ejec = seleccion_plan + [clientes[9]]  # D1 Fontibon -> Zona Occidente (180000)

    paradas_ejec = []
    for i, cli in enumerate(seleccion_ejec, start=1):
        extra_peso = 30 if i == 4 else 0  # una parada entrego mas producto de lo planeado
        tiempo_real = (20 + i * 2) + (10 if i == 2 else 0)  # una parada tomo mas tiempo real
        paradas_ejec.append(
            {
                "cliente_id": cli["id"],
                "secuencia": i,
                "tiempo_servicio_min": tiempo_real,
                "pedidos": [
                    {"producto_id": productos[0]["id"], "cantidad": 50 + extra_peso},
                    {"producto_id": productos[3]["id"], "cantidad": 20},
                ],
            }
        )

    ruta_ejec = post(
        "/rutas/importar/ejecutada",
        {
            "codigo_ruta": "RUTA-BOG-001",
            "centro_distribucion_id": cedi_norte["id"],
            "transportista_id": trans2["id"],
            "tarifa_transportista_id": tarifa_trans2_zona["id"],
            "tipo_camion_id": tipo_sencillo["id"],
            "fecha": "2026-06-25T07:00:00",
            "ruta_planificada_id": ruta_plan["id"],
            "paradas": paradas_ejec,
        },
    )
    print("Ruta ejecutada creada. ID:", ruta_ejec["id"], "| Costo real:", ruta_ejec["costo_flete_calculado"])
    print("Explicacion:", ruta_ejec["detalle_calculo"]["explicacion"])

    # ================= Segunda ruta planificada/ejecutada con TransRapido (POR_PARADA) =================
    print("\n== Ruta Planificada 2 (TransRapido, metodo POR_PARADA) ==")
    seleccion2 = [clientes[1], clientes[4], clientes[10], clientes[13]]
    paradas_plan2 = []
    for i, cli in enumerate(seleccion2, start=1):
        paradas_plan2.append(
            {
                "cliente_id": cli["id"],
                "secuencia": i,
                "tiempo_servicio_min": 15,
                "pedidos": [{"producto_id": productos[1]["id"], "cantidad": 30}],
            }
        )
    ruta_plan2 = post(
        "/rutas/importar/planificada",
        {
            "codigo_ruta": "RUTA-BOG-002",
            "centro_distribucion_id": cedi_norte["id"],
            "transportista_id": trans1["id"],
            "tarifa_transportista_id": tarifa_trans1_parada["id"],
            "tipo_camion_id": tipo_turbo["id"],
            "fecha": "2026-06-26T08:00:00",
            "paradas": paradas_plan2,
        },
    )
    print("Ruta planificada 2 creada. ID:", ruta_plan2["id"], "| Costo estimado:", ruta_plan2["costo_flete_calculado"])

    print("\n== Ruta Ejecutada 2 (una parada adicional no planificada) ==")
    seleccion2_real = seleccion2 + [clientes[11]]  # se agrego una parada extra en la ejecucion real
    paradas_ejec2 = []
    for i, cli in enumerate(seleccion2_real, start=1):
        paradas_ejec2.append(
            {
                "cliente_id": cli["id"],
                "secuencia": i,
                "tiempo_servicio_min": 15,
                "pedidos": [{"producto_id": productos[1]["id"], "cantidad": 30}],
            }
        )
    ruta_ejec2 = post(
        "/rutas/importar/ejecutada",
        {
            "codigo_ruta": "RUTA-BOG-002",
            "centro_distribucion_id": cedi_norte["id"],
            "transportista_id": trans1["id"],
            "tarifa_transportista_id": tarifa_trans1_parada["id"],
            "tipo_camion_id": tipo_turbo["id"],
            "fecha": "2026-06-26T08:00:00",
            "ruta_planificada_id": ruta_plan2["id"],
            "paradas": paradas_ejec2,
        },
    )
    print("Ruta ejecutada 2 creada. ID:", ruta_ejec2["id"], "| Costo real:", ruta_ejec2["costo_flete_calculado"])

    # ================= Ruta 3: TransRapido, metodo POR_VIAJE =================
    print("\n== Ruta Planificada 3 (TransRapido, metodo POR_VIAJE) ==")
    seleccion3 = [clientes[6], clientes[8]]
    paradas_plan3 = [
        {
            "cliente_id": cli["id"],
            "secuencia": i,
            "tiempo_servicio_min": 25,
            "pedidos": [{"producto_id": productos[2]["id"], "cantidad": 15}],
        }
        for i, cli in enumerate(seleccion3, start=1)
    ]
    ruta_plan3 = post(
        "/rutas/importar/planificada",
        {
            "codigo_ruta": "RUTA-BOG-003",
            "centro_distribucion_id": cedi_sur["id"],
            "transportista_id": trans1["id"],
            "tarifa_transportista_id": tarifa_trans1_viaje["id"],
            "tipo_camion_id": tipo_turbo["id"],
            "fecha": "2026-06-27T07:30:00",
            "paradas": paradas_plan3,
        },
    )
    print("Ruta planificada 3 (POR_VIAJE). ID:", ruta_plan3["id"], "| Costo estimado:", ruta_plan3["costo_flete_calculado"])
    print("Explicacion:", ruta_plan3["detalle_calculo"]["explicacion"])

    print("\n== Ruta Ejecutada 3 (mismo viaje, tarifa plana no cambia pese a diferencias) ==")
    paradas_ejec3 = [
        {
            "cliente_id": cli["id"],
            "secuencia": i,
            "tiempo_servicio_min": 40,
            "pedidos": [{"producto_id": productos[2]["id"], "cantidad": 18}],
        }
        for i, cli in enumerate(seleccion3, start=1)
    ]
    ruta_ejec3 = post(
        "/rutas/importar/ejecutada",
        {
            "codigo_ruta": "RUTA-BOG-003",
            "centro_distribucion_id": cedi_sur["id"],
            "transportista_id": trans1["id"],
            "tarifa_transportista_id": tarifa_trans1_viaje["id"],
            "tipo_camion_id": tipo_turbo["id"],
            "fecha": "2026-06-27T07:30:00",
            "ruta_planificada_id": ruta_plan3["id"],
            "paradas": paradas_ejec3,
        },
    )
    print("Ruta ejecutada 3 (POR_VIAJE). ID:", ruta_ejec3["id"], "| Costo real:", ruta_ejec3["costo_flete_calculado"],
          "(igual al planificado, como se espera en tarifa fija por viaje)")

    # ================= Ruta 4: LogiCarga, metodo POR_PESO_VOLUMEN (kg) =================
    print("\n== Ruta Planificada 4 (LogiCarga, metodo POR_PESO_VOLUMEN) ==")
    seleccion4 = [clientes[13], clientes[10], clientes[14]]
    paradas_plan4 = [
        {
            "cliente_id": cli["id"],
            "secuencia": i,
            "tiempo_servicio_min": 18,
            "pedidos": [
                {"producto_id": productos[3]["id"], "cantidad": 40},
                {"producto_id": productos[7]["id"], "cantidad": 25},
            ],
        }
        for i, cli in enumerate(seleccion4, start=1)
    ]
    ruta_plan4 = post(
        "/rutas/importar/planificada",
        {
            "codigo_ruta": "RUTA-BOG-004",
            "centro_distribucion_id": cedi_norte["id"],
            "transportista_id": trans2["id"],
            "tarifa_transportista_id": tarifa_trans2_peso["id"],
            "tipo_camion_id": tipo_sencillo["id"],
            "fecha": "2026-06-28T06:45:00",
            "paradas": paradas_plan4,
        },
    )
    print("Ruta planificada 4 (POR_PESO_VOLUMEN). ID:", ruta_plan4["id"], "| Costo estimado:", ruta_plan4["costo_flete_calculado"])
    print("Explicacion:", ruta_plan4["detalle_calculo"]["explicacion"])

    print("\n== Ruta Ejecutada 4 (se entrego mas peso del planificado) ==")
    paradas_ejec4 = [
        {
            "cliente_id": cli["id"],
            "secuencia": i,
            "tiempo_servicio_min": 18,
            "pedidos": [
                {"producto_id": productos[3]["id"], "cantidad": 45},
                {"producto_id": productos[7]["id"], "cantidad": 25},
            ],
        }
        for i, cli in enumerate(seleccion4, start=1)
    ]
    ruta_ejec4 = post(
        "/rutas/importar/ejecutada",
        {
            "codigo_ruta": "RUTA-BOG-004",
            "centro_distribucion_id": cedi_norte["id"],
            "transportista_id": trans2["id"],
            "tarifa_transportista_id": tarifa_trans2_peso["id"],
            "tipo_camion_id": tipo_sencillo["id"],
            "fecha": "2026-06-28T06:45:00",
            "ruta_planificada_id": ruta_plan4["id"],
            "paradas": paradas_ejec4,
        },
    )
    print("Ruta ejecutada 4 (POR_PESO_VOLUMEN). ID:", ruta_ejec4["id"], "| Costo real:", ruta_ejec4["costo_flete_calculado"])
    print("Explicacion:", ruta_ejec4["detalle_calculo"]["explicacion"])

    # ================= Ruta 5: Transportes del Valle, metodo POR_TIEMPO_SERVICIO =================
    print("\n== Ruta Planificada 5 (Transportes del Valle, metodo POR_TIEMPO_SERVICIO) ==")
    seleccion5 = [clientes[4], clientes[11]]
    paradas_plan5 = [
        {
            "cliente_id": cli["id"],
            "secuencia": i,
            "tiempo_servicio_min": 30,
            "pedidos": [{"producto_id": productos[5]["id"], "cantidad": 20}],
        }
        for i, cli in enumerate(seleccion5, start=1)
    ]
    ruta_plan5 = post(
        "/rutas/importar/planificada",
        {
            "codigo_ruta": "RUTA-BOG-005",
            "centro_distribucion_id": cedi_norte["id"],
            "transportista_id": trans3["id"],
            "tarifa_transportista_id": tarifa_trans3_tiempo["id"],
            "tipo_camion_id": tipo_nhr["id"],
            "fecha": "2026-06-29T09:00:00",
            "paradas": paradas_plan5,
        },
    )
    print("Ruta planificada 5 (POR_TIEMPO_SERVICIO). ID:", ruta_plan5["id"], "| Costo estimado:", ruta_plan5["costo_flete_calculado"])
    print("Explicacion:", ruta_plan5["detalle_calculo"]["explicacion"])

    print("\n== Ruta Ejecutada 5 (tiempos reales de atencion mayores) ==")
    paradas_ejec5 = [
        {
            "cliente_id": cli["id"],
            "secuencia": i,
            "tiempo_servicio_min": 45,
            "pedidos": [{"producto_id": productos[5]["id"], "cantidad": 20}],
        }
        for i, cli in enumerate(seleccion5, start=1)
    ]
    ruta_ejec5 = post(
        "/rutas/importar/ejecutada",
        {
            "codigo_ruta": "RUTA-BOG-005",
            "centro_distribucion_id": cedi_norte["id"],
            "transportista_id": trans3["id"],
            "tarifa_transportista_id": tarifa_trans3_tiempo["id"],
            "tipo_camion_id": tipo_nhr["id"],
            "fecha": "2026-06-29T09:00:00",
            "ruta_planificada_id": ruta_plan5["id"],
            "paradas": paradas_ejec5,
        },
    )
    print("Ruta ejecutada 5 (POR_TIEMPO_SERVICIO). ID:", ruta_ejec5["id"], "| Costo real:", ruta_ejec5["costo_flete_calculado"])
    print("Explicacion:", ruta_ejec5["detalle_calculo"]["explicacion"])

    # ================= Ruta 6: TransRapido, metodo POR_PARADA (camino REAL distinto al planificado) =================
    print("\n== Ruta Planificada 6 (TransRapido, metodo POR_PARADA, CEDI Sur) ==")
    # Planificado: San Jorge (Restrepo) -> Supermercado Kennedy -> Mayorista Corabastos
    seleccion6_plan = [clientes[14], clientes[6], clientes[5]]
    paradas_plan6 = [
        {
            "cliente_id": cli["id"],
            "secuencia": i,
            "tiempo_servicio_min": 20,
            "pedidos": [{"producto_id": productos[4]["id"], "cantidad": 25}],
        }
        for i, cli in enumerate(seleccion6_plan, start=1)
    ]
    ruta_plan6 = post(
        "/rutas/importar/planificada",
        {
            "codigo_ruta": "RUTA-BOG-006",
            "centro_distribucion_id": cedi_sur["id"],
            "transportista_id": trans1["id"],
            "tarifa_transportista_id": tarifa_trans1_parada["id"],
            "tipo_camion_id": tipo_turbo["id"],
            "fecha": "2026-06-30T07:15:00",
            "paradas": paradas_plan6,
        },
    )
    print("Ruta planificada 6 (POR_PARADA). ID:", ruta_plan6["id"], "| Costo estimado:", ruta_plan6["costo_flete_calculado"])

    print("\n== Ruta Ejecutada 6 (camino REAL distinto: se omitio Kennedy, se atendieron Bosa y Soacha en su lugar) ==")
    # Ejecutado: San Jorge (Restrepo) -> Tienda El Progreso (Bosa) -> Minimarket Soacha -> Mayorista Corabastos
    # Kennedy nunca se visito (cliente cerrado); en su lugar se atendieron 2 clientes distintos mas lejanos.
    # El trazado en el mapa (polilinea verde) sera visiblemente diferente al planificado (azul).
    seleccion6_ejec = [clientes[14], clientes[7], clientes[8], clientes[5]]
    paradas_ejec6 = [
        {
            "cliente_id": cli["id"],
            "secuencia": i,
            "tiempo_servicio_min": 20,
            "pedidos": [{"producto_id": productos[4]["id"], "cantidad": 25}],
        }
        for i, cli in enumerate(seleccion6_ejec, start=1)
    ]
    ruta_ejec6 = post(
        "/rutas/importar/ejecutada",
        {
            "codigo_ruta": "RUTA-BOG-006",
            "centro_distribucion_id": cedi_sur["id"],
            "transportista_id": trans1["id"],
            "tarifa_transportista_id": tarifa_trans1_parada["id"],
            "tipo_camion_id": tipo_turbo["id"],
            "fecha": "2026-06-30T07:15:00",
            "ruta_planificada_id": ruta_plan6["id"],
            "paradas": paradas_ejec6,
        },
    )
    print("Ruta ejecutada 6 (POR_PARADA). ID:", ruta_ejec6["id"], "| Costo real:", ruta_ejec6["costo_flete_calculado"],
          "(4 paradas reales vs 3 planificadas, 2 clientes distintos)")

    # ================= Ruta 7: Transportes del Valle, metodo POR_VIAJE (secuencia y clientes distintos) =================
    print("\n== Ruta Planificada 7 (Transportes del Valle, metodo POR_VIAJE, CEDI Norte) ==")
    # Planificado: Alkosto Calle 80 -> Dona Maria (Suba) -> Justo y Bueno (Engativa)
    seleccion7_plan = [clientes[13], clientes[11], clientes[10]]
    paradas_plan7 = [
        {
            "cliente_id": cli["id"],
            "secuencia": i,
            "tiempo_servicio_min": 22,
            "pedidos": [{"producto_id": productos[6]["id"], "cantidad": 35}],
        }
        for i, cli in enumerate(seleccion7_plan, start=1)
    ]
    ruta_plan7 = post(
        "/rutas/importar/planificada",
        {
            "codigo_ruta": "RUTA-BOG-007",
            "centro_distribucion_id": cedi_norte["id"],
            "transportista_id": trans3["id"],
            "tarifa_transportista_id": tarifa_trans3_viaje["id"],
            "tipo_camion_id": tipo_nhr["id"],
            "fecha": "2026-07-01T07:45:00",
            "paradas": paradas_plan7,
        },
    )
    print("Ruta planificada 7 (POR_VIAJE). ID:", ruta_plan7["id"], "| Costo estimado:", ruta_plan7["costo_flete_calculado"])

    print("\n== Ruta Ejecutada 7 (orden y clientes reales distintos: no se llego a Justo y Bueno, se desvio a Ara Usaquen) ==")
    # Ejecutado: Dona Maria (Suba) -> Ara Usaquen -> Alkosto Calle 80 (orden invertido + cliente distinto,
    # Justo y Bueno quedo sin atender por cierre del local). Trazado real claramente distinto en el mapa.
    seleccion7_ejec = [clientes[11], clientes[3], clientes[13]]
    paradas_ejec7 = [
        {
            "cliente_id": cli["id"],
            "secuencia": i,
            "tiempo_servicio_min": 22,
            "pedidos": [{"producto_id": productos[6]["id"], "cantidad": 35}],
        }
        for i, cli in enumerate(seleccion7_ejec, start=1)
    ]
    ruta_ejec7 = post(
        "/rutas/importar/ejecutada",
        {
            "codigo_ruta": "RUTA-BOG-007",
            "centro_distribucion_id": cedi_norte["id"],
            "transportista_id": trans3["id"],
            "tarifa_transportista_id": tarifa_trans3_viaje["id"],
            "tipo_camion_id": tipo_nhr["id"],
            "fecha": "2026-07-01T07:45:00",
            "ruta_planificada_id": ruta_plan7["id"],
            "paradas": paradas_ejec7,
        },
    )
    print("Ruta ejecutada 7 (POR_VIAJE). ID:", ruta_ejec7["id"], "| Costo real:", ruta_ejec7["costo_flete_calculado"],
          "(igual al planificado por ser tarifa plana, pese al cambio de recorrido)")

    # ================= Ruta 8 (v2): LogiCarga, metodo POR_KILOMETRO =================
    print("\n== Ruta Planificada 8 (LogiCarga, metodo POR_KILOMETRO) ==")
    # Se fijan distancia_km_tramo explicitas (no se usa el fallback Haversine) para
    # que el costo esperado sea verificable de forma determinista: 2500/km.
    seleccion8 = [clientes[2], clientes[13]]  # Carulla 85, Alkosto Calle 80 (Zona Norte)
    paradas_plan8 = [
        {
            "cliente_id": seleccion8[0]["id"],
            "secuencia": 1,
            "distancia_km_tramo": 8.4,
            "tiempo_transito_min_tramo": 18,
            "tiempo_servicio_min": 20,
            "pedidos": [{"producto_id": productos[0]["id"], "cantidad": 20}],
        },
        {
            "cliente_id": seleccion8[1]["id"],
            "secuencia": 2,
            "distancia_km_tramo": 6.1,
            "tiempo_transito_min_tramo": 14,
            "tiempo_servicio_min": 20,
            "pedidos": [{"producto_id": productos[0]["id"], "cantidad": 20}],
        },
    ]
    ruta_plan8 = post(
        "/rutas/importar/planificada",
        {
            "codigo_ruta": "RUTA-BOG-008",
            "centro_distribucion_id": cedi_norte["id"],
            "transportista_id": trans2["id"],
            "tarifa_transportista_id": tarifa_trans2_km["id"],
            "tipo_camion_id": tipo_sencillo["id"],
            "fecha": "2026-07-02T07:00:00",
            "paradas": paradas_plan8,
        },
    )
    print("Ruta planificada 8 (POR_KILOMETRO). ID:", ruta_plan8["id"], "| Costo estimado:", ruta_plan8["costo_flete_calculado"])
    print("Explicacion:", ruta_plan8["detalle_calculo"]["explicacion"])

    print("\n== Ruta Ejecutada 8 (recorrido real mas largo por trafico/desvio) ==")
    # Distancias reales mayores a las planificadas para que la conciliacion muestre
    # una diferencia positiva clara en el costo POR_KILOMETRO.
    paradas_ejec8 = [
        {
            "cliente_id": seleccion8[0]["id"],
            "secuencia": 1,
            "distancia_km_tramo": 10.2,
            "tiempo_transito_min_tramo": 25,
            "tiempo_servicio_min": 22,
            "pedidos": [{"producto_id": productos[0]["id"], "cantidad": 20}],
        },
        {
            "cliente_id": seleccion8[1]["id"],
            "secuencia": 2,
            "distancia_km_tramo": 8.9,
            "tiempo_transito_min_tramo": 21,
            "tiempo_servicio_min": 20,
            "pedidos": [{"producto_id": productos[0]["id"], "cantidad": 20}],
        },
    ]
    ruta_ejec8 = post(
        "/rutas/importar/ejecutada",
        {
            "codigo_ruta": "RUTA-BOG-008",
            "centro_distribucion_id": cedi_norte["id"],
            "transportista_id": trans2["id"],
            "tarifa_transportista_id": tarifa_trans2_km["id"],
            "tipo_camion_id": tipo_sencillo["id"],
            "fecha": "2026-07-02T07:00:00",
            "ruta_planificada_id": ruta_plan8["id"],
            "paradas": paradas_ejec8,
        },
    )
    print("Ruta ejecutada 8 (POR_KILOMETRO). ID:", ruta_ejec8["id"], "| Costo real:", ruta_ejec8["costo_flete_calculado"])
    print("Explicacion:", ruta_ejec8["detalle_calculo"]["explicacion"])

    # ================= Ruta 9 (v2): TransRapido, POR_VIAJE con tarifa especifica de camion NHR =================
    print("\n== Ruta Planificada 9 (TransRapido, POR_VIAJE, tarifa restringida a camion NHR) ==")
    # Misma metodologia (POR_VIAJE) y mismo transportista que la Ruta 3, pero usando
    # la tarifa mas barata reservada para camion NHR ($180,000) en vez de la general
    # ($250,000). Demuestra que el mismo metodo de tarifa da un costo distinto segun
    # el tipo de camion asignado a la ruta.
    seleccion9 = [clientes[4], clientes[11]]  # Tienda La Esquina (Usaquen), Dona Maria (Suba)
    paradas_plan9 = [
        {
            "cliente_id": cli["id"],
            "secuencia": i,
            "tiempo_servicio_min": 18,
            "pedidos": [{"producto_id": productos[5]["id"], "cantidad": 12}],
        }
        for i, cli in enumerate(seleccion9, start=1)
    ]
    ruta_plan9 = post(
        "/rutas/importar/planificada",
        {
            "codigo_ruta": "RUTA-BOG-009",
            "centro_distribucion_id": cedi_norte["id"],
            "transportista_id": trans1["id"],
            "tarifa_transportista_id": tarifa_trans1_viaje_nhr["id"],
            "tipo_camion_id": tipo_nhr["id"],
            "fecha": "2026-07-02T08:30:00",
            "paradas": paradas_plan9,
        },
    )
    print("Ruta planificada 9 (POR_VIAJE, tarifa NHR). ID:", ruta_plan9["id"],
          "| Costo estimado:", ruta_plan9["costo_flete_calculado"],
          "(vs $250,000 que costaria con la tarifa general de TransRapido para otro tipo de camion)")

    print("\n== Ruta Ejecutada 9 (mismo viaje, misma tarifa NHR) ==")
    paradas_ejec9 = [
        {
            "cliente_id": cli["id"],
            "secuencia": i,
            "tiempo_servicio_min": 22,
            "pedidos": [{"producto_id": productos[5]["id"], "cantidad": 14}],
        }
        for i, cli in enumerate(seleccion9, start=1)
    ]
    ruta_ejec9 = post(
        "/rutas/importar/ejecutada",
        {
            "codigo_ruta": "RUTA-BOG-009",
            "centro_distribucion_id": cedi_norte["id"],
            "transportista_id": trans1["id"],
            "tarifa_transportista_id": tarifa_trans1_viaje_nhr["id"],
            "tipo_camion_id": tipo_nhr["id"],
            "fecha": "2026-07-02T08:30:00",
            "ruta_planificada_id": ruta_plan9["id"],
            "paradas": paradas_ejec9,
        },
    )
    print("Ruta ejecutada 9 (POR_VIAJE, tarifa NHR). ID:", ruta_ejec9["id"], "| Costo real:", ruta_ejec9["costo_flete_calculado"])

    print("\n== Validacion: una tarifa restringida a NHR no se puede usar con otro camion ==")
    try:
        post(
            "/rutas/importar/planificada",
            {
                "codigo_ruta": "RUTA-BOG-009-INVALIDA",
                "centro_distribucion_id": cedi_norte["id"],
                "transportista_id": trans1["id"],
                "tarifa_transportista_id": tarifa_trans1_viaje_nhr["id"],
                "tipo_camion_id": tipo_sencillo["id"],  # camion distinto al de la tarifa (NHR) -> debe fallar
                "fecha": "2026-07-02T08:30:00",
                "paradas": paradas_plan9,
            },
        )
        print("ERROR: se esperaba que la importacion fallara por incompatibilidad de tipo de camion.")
    except Exception as e:
        print("OK, la importacion fue rechazada como se esperaba:", str(e)[:200])

    print("\n== Conciliacion ==")
    conciliacion = get("/conciliacion/rutas")
    for c in conciliacion:
        print(c)

    print("\nSEED COMPLETADO EXITOSAMENTE.")


if __name__ == "__main__":
    main()
