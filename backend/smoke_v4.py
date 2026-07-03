"""Smoke test manual de v4: login, roles, aislamiento por empresa.
Corre con sqlite en memoria/archivo temporal, sin tocar la base real.
"""
import os

os.environ["DATABASE_URL"] = "sqlite:////tmp/smoke_v4_run.db"

import subprocess
subprocess.run(["rm", "-f", "/tmp/smoke_v4_run.db"])

from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import models
from app import auth

client = TestClient(app)

db = SessionLocal()

# 1. Crear super admin directamente en DB (bootstrap, como se hara en produccion)
super_admin = models.Usuario(
    nombre="Super Admin",
    email="super@fleteapp.com",
    password_hash=auth.hash_password("super123"),
    rol="SUPER_ADMIN",
    empresa_id=None,
    activo=True,
)
db.add(super_admin)
db.commit()
db.refresh(super_admin)

# 2. Login como super admin
r = client.post("/api/auth/login", json={"email": "super@fleteapp.com", "password": "super123"})
assert r.status_code == 200, r.text
token_super = r.json()["access_token"]
print("OK: login super admin")

H_SUPER = {"Authorization": f"Bearer {token_super}"}

# 3. Login con contrasena mala falla
r = client.post("/api/auth/login", json={"email": "super@fleteapp.com", "password": "mala"})
assert r.status_code == 401
print("OK: login con password incorrecta rechazado (401)")

# 4. Sin token, un endpoint protegido da 401/403
r = client.get("/api/empresas/")
assert r.status_code in (401, 403), r.text
print(f"OK: endpoint sin token rechazado ({r.status_code})")

# 5. Super admin crea 2 empresas
r = client.post("/api/empresas/", json={"nombre": "Empresa Uno", "nit": "111"}, headers=H_SUPER)
assert r.status_code == 200, r.text
empresa1 = r.json()
r = client.post("/api/empresas/", json={"nombre": "Empresa Dos", "nit": "222"}, headers=H_SUPER)
assert r.status_code == 200, r.text
empresa2 = r.json()
print(f"OK: 2 empresas creadas (ids {empresa1['id']}, {empresa2['id']})")

# 6. Verificar que MetodoTarifa se sembro automaticamente para cada empresa
metodos1 = db.query(models.MetodoTarifa).filter(models.MetodoTarifa.empresa_id == empresa1["id"]).all()
metodos2 = db.query(models.MetodoTarifa).filter(models.MetodoTarifa.empresa_id == empresa2["id"]).all()
assert len(metodos1) == 6, f"esperaba 6 metodos, encontre {len(metodos1)}"
assert len(metodos2) == 6, f"esperaba 6 metodos, encontre {len(metodos2)}"
print("OK: 6 metodos de tarifa sembrados automaticamente por empresa")

# 7. Super admin crea un EMPRESA_ADMIN para cada empresa
r = client.post(
    "/api/usuarios/",
    json={"nombre": "Admin Uno", "email": "admin1@e1.com", "password": "pass1", "rol": "EMPRESA_ADMIN", "empresa_id": empresa1["id"]},
    headers=H_SUPER,
)
assert r.status_code == 200, r.text
r = client.post(
    "/api/usuarios/",
    json={"nombre": "Admin Dos", "email": "admin2@e2.com", "password": "pass2", "rol": "EMPRESA_ADMIN", "empresa_id": empresa2["id"]},
    headers=H_SUPER,
)
assert r.status_code == 200, r.text
print("OK: EMPRESA_ADMIN creado para cada empresa")

# 8. Un EMPRESA_ADMIN NO puede crear usuarios (solo SUPER_ADMIN)
r = client.post("/api/auth/login", json={"email": "admin1@e1.com", "password": "pass1"})
token_admin1 = r.json()["access_token"]
H_ADMIN1 = {"Authorization": f"Bearer {token_admin1}"}
r = client.post(
    "/api/usuarios/",
    json={"nombre": "Hack", "email": "x@x.com", "password": "x", "rol": "USUARIO_FINAL", "empresa_id": empresa1["id"]},
    headers=H_ADMIN1,
)
assert r.status_code == 403, r.text
print("OK: EMPRESA_ADMIN no puede crear usuarios (403)")

# 9. EMPRESA_ADMIN de empresa1 crea una zona geografica -- debe quedar con su empresa_id automatico
r = client.post(
    "/api/zonas-geograficas/",
    json={"nombre": "Zona Norte E1", "descripcion": "test", "tarifa_zona": 10000},
    headers=H_ADMIN1,
)
assert r.status_code == 200, r.text
zona1 = r.json()
assert zona1["empresa_id"] == empresa1["id"]
print("OK: zona creada por admin1 queda con empresa_id de empresa1 (inyectado por servidor, no por el cliente)")

# 10. Login admin2 (empresa2), listar zonas -- NO debe ver la zona de empresa1
r = client.post("/api/auth/login", json={"email": "admin2@e2.com", "password": "pass2"})
token_admin2 = r.json()["access_token"]
H_ADMIN2 = {"Authorization": f"Bearer {token_admin2}"}
r = client.get("/api/zonas-geograficas/", headers=H_ADMIN2)
assert r.status_code == 200
zonas_vistas_por_e2 = r.json()
assert all(z["id"] != zona1["id"] for z in zonas_vistas_por_e2), "FUGA: empresa2 ve una zona de empresa1!"
print(f"OK: admin2 NO ve la zona de empresa1 (ve {len(zonas_vistas_por_e2)} zonas propias)")

# 11. admin2 intenta leer DIRECTAMENTE por id la zona de empresa1 -- debe dar 404, no 200
r = client.get(f"/api/zonas-geograficas/{zona1['id']}", headers=H_ADMIN2)
assert r.status_code == 404, f"FUGA: admin2 pudo leer zona de empresa1 por id directo! status={r.status_code}"
print("OK: admin2 no puede leer por id directo un registro de empresa1 (404)")

# 12. admin2 intenta EDITAR la zona de empresa1 -- debe dar 404
r = client.put(
    f"/api/zonas-geograficas/{zona1['id']}",
    json={"nombre": "hackeado", "descripcion": "x", "tarifa_zona": 0},
    headers=H_ADMIN2,
)
assert r.status_code == 404, f"FUGA: admin2 pudo editar zona de empresa1! status={r.status_code}"
print("OK: admin2 no puede editar un registro de empresa1 (404)")

# 13. SUPER_ADMIN SI puede ver la zona de empresa1 usando ?empresa_id=
r = client.get(f"/api/zonas-geograficas/?empresa_id={empresa1['id']}", headers=H_SUPER)
assert r.status_code == 200
assert any(z["id"] == zona1["id"] for z in r.json())
print("OK: SUPER_ADMIN ve la zona de empresa1 pasando ?empresa_id=")

# 14. SUPER_ADMIN sin filtro ve TODAS las zonas de todas las empresas
r = client.get("/api/zonas-geograficas/", headers=H_SUPER)
assert r.status_code == 200
ids_vistos = {z["id"] for z in r.json()}
assert zona1["id"] in ids_vistos
print(f"OK: SUPER_ADMIN sin filtro ve todas las zonas ({len(ids_vistos)} en total)")

# 15. USUARIO_FINAL no puede acceder a maestros (solo mapa/conciliacion)
r = client.post(
    "/api/usuarios/",
    json={"nombre": "Final Uno", "email": "final1@e1.com", "password": "pf1", "rol": "USUARIO_FINAL", "empresa_id": empresa1["id"]},
    headers=H_SUPER,
)
assert r.status_code == 200, r.text
r = client.post("/api/auth/login", json={"email": "final1@e1.com", "password": "pf1"})
token_final1 = r.json()["access_token"]
H_FINAL1 = {"Authorization": f"Bearer {token_final1}"}
r = client.get("/api/zonas-geograficas/", headers=H_FINAL1)
assert r.status_code == 403, f"USUARIO_FINAL no deberia poder ver zonas geograficas! status={r.status_code}"
print("OK: USUARIO_FINAL no puede ver maestros (403)")
r = client.get("/api/conciliacion/rutas", headers=H_FINAL1)
assert r.status_code == 200, r.text
print("OK: USUARIO_FINAL SI puede ver conciliacion")

# 16. token invalido/manipulado -> 401
r = client.get("/api/empresas/", headers={"Authorization": "Bearer token-invalido"})
assert r.status_code == 401, r.text
print("OK: token invalido rechazado (401)")

print("\nTODOS LOS SMOKE TESTS DE v4 PASARON")
