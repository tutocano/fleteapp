"""
Backfill de v4 (usuarios, roles, multi-empresa). Correr DESPUES de:
  1. Ejecutar migrate_v4_alter.sql contra produccion (agrega las columnas
     empresa_id nuevas, todavia nullable, y quita los UNIQUE globales viejos).
  2. Desplegar el codigo nuevo (para que Base.metadata.create_all() cree la
     tabla `usuario` si migrate_v4_alter.sql no se corrio -- de todas formas
     no hace dano correrlo dos veces, es idempotente).

Que hace, en orden:
  A. Toma la primera Empresa que ya exista en la base (la real, la que se creo
     con seed.py: "Distribuidora ConsumoMasivo S.A.S.") y le asigna su
     empresa_id a TODOS los registros existentes de tipo_cliente,
     zona_geografica, tipo_camion, producto, metodo_tarifa, flota,
     tarifa_transportista y ruta que todavia no tengan empresa_id. Esto NO
     mueve ni divide los datos reales -- se quedan intactos con la empresa
     real, para no arriesgar informacion de produccion ya validada.
  B. Pone NOT NULL en las columnas empresa_id de esas tablas y crea los
     indices UNIQUE compuestos (empresa_id, codigo)/(empresa_id, nombre) que
     reemplazan a los UNIQUE globales que se quitaron en el paso SQL anterior.
  C. Crea una segunda empresa "Empresa Demo 2" (si no existe ya) con su
     PROPIO set de datos de prueba, autocontenido (propia zona, tipo de
     camion, tipo de cliente, producto, metodo de tarifa -- clonado
     automatico --, un CEDI, un transportista con una tarifa, 2 clientes y
     una ruta planificada + ejecutada). Asi terminas con 2 empresas reales en
     produccion para poder probar que el aislamiento funciona: la empresa 1
     jamas debe ver nada de la Empresa Demo 2 y viceversa, y el SUPER_ADMIN
     debe ver ambas.
  D. Crea el primer usuario SUPER_ADMIN (a partir de las variables de entorno
     SUPER_ADMIN_EMAIL / SUPER_ADMIN_PASSWORD, obligatorias) si todavia no
     existe ninguno -- es el huevo-y-gallina: sin este usuario no se puede
     entrar a crear los demas desde la pantalla de Usuarios.

Es idempotente: se puede correr varias veces sin duplicar nada (revisa qué ya
existe antes de crear).

Uso local (docker-compose):
    docker compose exec backend \
      -e SUPER_ADMIN_EMAIL="admin@fleteapp.com" -e SUPER_ADMIN_PASSWORD="cambia-esto" \
      python migrate_v4_backfill.py

Uso contra produccion en Render (mismo patron que los backfills anteriores):
    docker run -it --rm \
      -e DATABASE_URL="<tu External Database URL>/flete_db" \
      -e SUPER_ADMIN_EMAIL="tu-correo@ejemplo.com" \
      -e SUPER_ADMIN_PASSWORD="una-contrasena-fuerte" \
      -v "$(pwd)/backend:/app" -w /app python:3.11-slim \
      bash -c "pip install -q -r requirements.txt && python migrate_v4_backfill.py"
"""
import os
from datetime import datetime

from sqlalchemy import text

from app.database import SessionLocal
from app.models import models
from app import auth
from app.routers.maestros import sembrar_metodos_tarifa_para_empresa
from app.services.flete_calculo import calcular_y_guardar


def _backfill_empresa_id_existente(db, empresa1_id: int):
    print(f"\n== Paso A: asignar empresa_id={empresa1_id} a catalogos existentes sin empresa ==")

    tablas_directas = [
        (models.TipoCliente, "tipo_cliente"),
        (models.ZonaGeografica, "zona_geografica"),
        (models.TipoCamion, "tipo_camion"),
        (models.Producto, "producto"),
        (models.MetodoTarifa, "metodo_tarifa"),
    ]
    for modelo, nombre in tablas_directas:
        pendientes = db.query(modelo).filter(modelo.empresa_id.is_(None)).all()
        for obj in pendientes:
            obj.empresa_id = empresa1_id
        print(f"  {nombre}: {len(pendientes)} filas actualizadas")

    pendientes_flota = db.query(models.Flota).filter(models.Flota.empresa_id.is_(None)).all()
    for f in pendientes_flota:
        f.empresa_id = f.transportista.empresa_id
    print(f"  flota: {len(pendientes_flota)} filas actualizadas (via transportista)")

    pendientes_tarifa = (
        db.query(models.TarifaTransportista).filter(models.TarifaTransportista.empresa_id.is_(None)).all()
    )
    for t in pendientes_tarifa:
        t.empresa_id = t.transportista.empresa_id
    print(f"  tarifa_transportista: {len(pendientes_tarifa)} filas actualizadas (via transportista)")

    pendientes_ruta = db.query(models.Ruta).filter(models.Ruta.empresa_id.is_(None)).all()
    for r in pendientes_ruta:
        r.empresa_id = r.centro_distribucion.empresa_id
    print(f"  ruta: {len(pendientes_ruta)} filas actualizadas (via centro_distribucion)")

    db.commit()


def _aplicar_not_null_y_constraints(db):
    print("\n== Paso B: NOT NULL + UNIQUE compuestos ==")
    if db.bind.dialect.name != "postgresql":
        print(
            f"  Dialecto '{db.bind.dialect.name}' detectado (no postgresql) -- se omite este "
            "paso (ALTER COLUMN/ADD CONSTRAINT con esta sintaxis es especifico de Postgres). "
            "Util para probar el resto del script localmente con SQLite; en produccion "
            "(Postgres) este paso si se ejecuta."
        )
        return
    sentencias = [
        "ALTER TABLE tipo_cliente ALTER COLUMN empresa_id SET NOT NULL",
        "ALTER TABLE zona_geografica ALTER COLUMN empresa_id SET NOT NULL",
        "ALTER TABLE tipo_camion ALTER COLUMN empresa_id SET NOT NULL",
        "ALTER TABLE producto ALTER COLUMN empresa_id SET NOT NULL",
        "ALTER TABLE metodo_tarifa ALTER COLUMN empresa_id SET NOT NULL",
        "ALTER TABLE flota ALTER COLUMN empresa_id SET NOT NULL",
        "ALTER TABLE tarifa_transportista ALTER COLUMN empresa_id SET NOT NULL",
        "ALTER TABLE ruta ALTER COLUMN empresa_id SET NOT NULL",
    ]
    for s in sentencias:
        db.execute(text(s))

    constraints = [
        ("uq_tipo_cliente_empresa_nombre", "ALTER TABLE tipo_cliente ADD CONSTRAINT uq_tipo_cliente_empresa_nombre UNIQUE (empresa_id, nombre)"),
        ("uq_producto_empresa_codigo", "ALTER TABLE producto ADD CONSTRAINT uq_producto_empresa_codigo UNIQUE (empresa_id, codigo)"),
        ("uq_metodo_tarifa_empresa_codigo", "ALTER TABLE metodo_tarifa ADD CONSTRAINT uq_metodo_tarifa_empresa_codigo UNIQUE (empresa_id, codigo)"),
        ("uq_centro_distribucion_empresa_codigo", "ALTER TABLE centro_distribucion ADD CONSTRAINT uq_centro_distribucion_empresa_codigo UNIQUE (empresa_id, codigo)"),
        ("uq_cliente_empresa_codigo", "ALTER TABLE cliente ADD CONSTRAINT uq_cliente_empresa_codigo UNIQUE (empresa_id, codigo)"),
    ]
    for nombre, sql in constraints:
        existe = db.execute(
            text("SELECT 1 FROM pg_constraint WHERE conname = :n"), {"n": nombre}
        ).first()
        if existe:
            print(f"  {nombre}: ya existia, se deja igual")
            continue
        db.execute(text(sql))
        print(f"  {nombre}: creado")

    db.commit()


def _get_or_create(db, modelo, filtro: dict, defaults: dict):
    """Get-or-create simple: busca por `filtro`, si no existe lo crea con
    filtro+defaults. Hace que toda esta funcion sea segura de re-correr aunque
    haya quedado a medias por un error anterior (ej. una tabla de v3 que
    todavia no se habia migrado en un ambiente local)."""
    obj = db.query(modelo).filter_by(**filtro).first()
    if obj:
        return obj, False
    obj = modelo(**filtro, **defaults)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj, True


def _crear_empresa_demo_2(db):
    print("\n== Paso C: crear 'Empresa Demo 2' con datos de prueba propios ==")

    empresa2, creada = _get_or_create(
        db, models.Empresa, {"nombre": "Empresa Demo 2"},
        {
            "nit": "900999888-1", "direccion": "Cra 7 # 10-20, Medellin",
            "telefono": "604-555-9999", "email": "operaciones@empresademo2.co",
        },
    )
    print(f"  Empresa Demo 2: {'creada' if creada else 'ya existia'} (id {empresa2.id})")

    sembrar_metodos_tarifa_para_empresa(db, empresa2.id)
    print("  6 metodos de tarifa clonados/verificados para Empresa Demo 2")

    cedi, _ = _get_or_create(
        db, models.CentroDistribucion, {"empresa_id": empresa2.id, "codigo": "CEDI-MED"},
        {"nombre": "CEDI Medellin", "latitud": 6.2442, "longitud": -75.5812, "direccion": "Cra 7 # 10-20, Medellin"},
    )
    tipo_cliente, _ = _get_or_create(
        db, models.TipoCliente, {"empresa_id": empresa2.id, "nombre": "General"},
        {"descripcion": "Tipo generico de prueba"},
    )
    zona, _ = _get_or_create(
        db, models.ZonaGeografica, {"empresa_id": empresa2.id, "nombre": "Zona Medellin Centro"},
        {"descripcion": "Zona de prueba", "tarifa_zona": 70000},
    )
    tipo_camion, _ = _get_or_create(
        db, models.TipoCamion, {"empresa_id": empresa2.id, "nombre": "NHR"},
        {"capacidad_peso_kg": 2500, "capacidad_volumen_m3": 12},
    )
    _get_or_create(
        db, models.Producto, {"empresa_id": empresa2.id, "codigo": "DEMO-001"},
        {"nombre": "Producto Demo", "peso_unitario_kg": 1.0, "volumen_unitario_m3": 0.001},
    )

    cliente1, _ = _get_or_create(
        db, models.Cliente, {"empresa_id": empresa2.id, "codigo": "CLI-D2-001"},
        {
            "tipo_cliente_id": tipo_cliente.id, "zona_geografica_id": zona.id,
            "nombre": "Cliente Demo Uno", "latitud": 6.2518, "longitud": -75.5636,
            "direccion": "Cliente Demo Uno, Medellin", "canal": "Demo",
        },
    )
    cliente2, _ = _get_or_create(
        db, models.Cliente, {"empresa_id": empresa2.id, "codigo": "CLI-D2-002"},
        {
            "tipo_cliente_id": tipo_cliente.id, "zona_geografica_id": zona.id,
            "nombre": "Cliente Demo Dos", "latitud": 6.2100, "longitud": -75.5900,
            "direccion": "Cliente Demo Dos, Medellin", "canal": "Demo",
        },
    )
    transportista, _ = _get_or_create(
        db, models.Transportista, {"empresa_id": empresa2.id, "nit": "900777666-1"},
        {"nombre": "Transportes Demo 2", "contacto": "Contacto Demo", "telefono": "300-000-0000"},
    )

    metodo_viaje = (
        db.query(models.MetodoTarifa)
        .filter(models.MetodoTarifa.empresa_id == empresa2.id, models.MetodoTarifa.codigo == "POR_VIAJE")
        .first()
    )
    tarifa, _ = _get_or_create(
        db, models.TarifaTransportista,
        {"empresa_id": empresa2.id, "transportista_id": transportista.id, "metodo_tarifa_id": metodo_viaje.id},
        {
            "tipo_camion_id": None, "nombre": "Tarifa plana por viaje - Demo 2",
            "valor_unitario": 150000, "unidad": "VIAJE", "activo": True,
        },
    )

    print(f"  CEDI, tipo de cliente, zona, tipo de camion, producto, 2 clientes, transportista y tarifa listos para Empresa Demo 2 (id {empresa2.id})")

    ruta_plan = (
        db.query(models.Ruta)
        .filter(models.Ruta.empresa_id == empresa2.id, models.Ruta.codigo_ruta == "RUTA-DEMO2-001")
        .first()
    )
    if ruta_plan:
        print(f"  Ruta de prueba ya existia para Empresa Demo 2 (id {ruta_plan.id})")
        return empresa2

    ruta_plan = models.Ruta(
        empresa_id=empresa2.id, codigo_ruta="RUTA-DEMO2-001", es_planificada=True,
        centro_distribucion_id=cedi.id, transportista_id=transportista.id,
        tarifa_transportista_id=tarifa.id, tipo_camion_id=tipo_camion.id,
        fecha=datetime(2026, 7, 1, 8, 0, 0), estado="PLANIFICADA",
    )
    db.add(ruta_plan)
    db.flush()
    parada1 = models.ParadaRuta(
        ruta_id=ruta_plan.id, cliente_id=cliente1.id, secuencia=1,
        distancia_km_tramo=5.0, tiempo_transito_min_tramo=12, tiempo_servicio_min=15,
    )
    parada2 = models.ParadaRuta(
        ruta_id=ruta_plan.id, cliente_id=cliente2.id, secuencia=2,
        distancia_km_tramo=4.0, tiempo_transito_min_tramo=10, tiempo_servicio_min=15,
    )
    db.add_all([parada1, parada2])
    db.commit()
    db.refresh(ruta_plan)
    calcular_y_guardar(db, ruta_plan)
    print(f"  Ruta planificada de prueba creada para Empresa Demo 2 (id {ruta_plan.id})")

    return empresa2


def _bootstrap_super_admin(db):
    print("\n== Paso D: usuario SUPER_ADMIN inicial ==")
    ya_existe = db.query(models.Usuario).filter(models.Usuario.rol == "SUPER_ADMIN").first()
    if ya_existe:
        print(f"  Ya existe un SUPER_ADMIN ({ya_existe.email}), no se crea otro.")
        return

    email = os.getenv("SUPER_ADMIN_EMAIL", "").strip()
    password = os.getenv("SUPER_ADMIN_PASSWORD", "").strip()
    if not email or not password:
        print(
            "  ADVERTENCIA: no se creo ningun SUPER_ADMIN porque faltan las variables de "
            "entorno SUPER_ADMIN_EMAIL y/o SUPER_ADMIN_PASSWORD. Vuelve a correr este script "
            "con esas 2 variables definidas para crear el primer usuario (sin el, no podras "
            "entrar al sistema)."
        )
        return

    usuario = models.Usuario(
        nombre="Super Admin", email=email, password_hash=auth.hash_password(password),
        rol="SUPER_ADMIN", empresa_id=None, activo=True,
    )
    db.add(usuario)
    db.commit()
    print(f"  SUPER_ADMIN creado: {email}")


def main():
    db = SessionLocal()
    try:
        empresas = db.query(models.Empresa).order_by(models.Empresa.id).all()
        if not empresas:
            # Base de datos nueva (ej. primera vez con docker compose en local): no hay
            # nada que "repartir" todavia -- create_all() ya crea las tablas con
            # empresa_id NOT NULL desde el inicio, asi que no hace falta backfill. Se
            # salta directo a crear Empresa Demo 2 y el primer SUPER_ADMIN, que es
            # justo lo que hace falta para poder entrar y empezar a usar el sistema.
            print(
                "No hay ninguna Empresa todavia (base de datos nueva) -- se omite el "
                "backfill de datos existentes y se crea directamente Empresa Demo 2 "
                "y el primer SUPER_ADMIN."
            )
        else:
            empresa1 = empresas[0]
            print(f"Empresa existente detectada: '{empresa1.nombre}' (id {empresa1.id}) -- se usara para el backfill.")
            _backfill_empresa_id_existente(db, empresa1.id)
            _aplicar_not_null_y_constraints(db)

        _crear_empresa_demo_2(db)
        _bootstrap_super_admin(db)

        print("\nMIGRACION v4 COMPLETADA.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
