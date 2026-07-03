"""
Autenticacion y autorizacion (v4): JWT + roles + aislamiento por empresa.

Piezas:
- hash_password / verify_password: bcrypt directo (no passlib, para evitar los
  problemas de compatibilidad de versiones conocidos de passlib+bcrypt).
- crear_token / decodificar_token: JWT con pyjwt, expira a las 12 horas, sin
  refresh token (decision confirmada con el usuario).
- get_current_user: dependencia de FastAPI que valida el token del header
  Authorization y carga el Usuario autenticado.
- require_role(*roles): dependencia que rechaza con 403 si el rol del usuario
  actual no esta permitido para ese endpoint.
- empresa_actual: dependencia central de aislamiento. Regla de oro: el
  empresa_id NUNCA se confia si viene del cliente (body/query) para roles
  distintos de SUPER_ADMIN -- siempre se toma del usuario autenticado.
"""
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import models

# En produccion se debe definir JWT_SECRET_KEY como variable de entorno propia.
# El valor por defecto solo sirve para desarrollo local.
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key-cambiar-en-produccion")
ALGORITHM = "HS256"
EXPIRACION_HORAS = 12

_bearer_scheme = HTTPBearer()


# ---------- Password hashing ----------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


# ---------- JWT ----------
def crear_token(usuario: models.Usuario) -> str:
    ahora = datetime.now(timezone.utc)
    payload = {
        "sub": str(usuario.id),
        "email": usuario.email,
        "rol": usuario.rol,
        "empresa_id": usuario.empresa_id,
        "iat": ahora,
        "exp": ahora + timedelta(hours=EXPIRACION_HORAS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def _decodificar_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="La sesion expiro, inicia sesion de nuevo",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido",
        )


# ---------- Dependencias FastAPI ----------
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> models.Usuario:
    payload = _decodificar_token(credentials.credentials)
    usuario_id = payload.get("sub")
    usuario = db.query(models.Usuario).filter(models.Usuario.id == int(usuario_id)).first()
    if usuario is None or not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado o inactivo",
        )
    return usuario


def require_role(*roles_permitidos: str):
    """Dependencia: rechaza con 403 si el rol del usuario actual no esta en roles_permitidos.
    SUPER_ADMIN siempre pasa, sin importar la lista (tiene acceso a todo)."""

    def _checker(usuario: models.Usuario = Depends(get_current_user)) -> models.Usuario:
        if usuario.rol == "SUPER_ADMIN":
            return usuario
        if usuario.rol not in roles_permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Tu rol ({usuario.rol}) no tiene permiso para esta accion",
            )
        return usuario

    return _checker


def empresa_actual(
    empresa_id: Optional[int] = None,
    usuario: models.Usuario = Depends(get_current_user),
) -> Optional[int]:
    """Devuelve el empresa_id que se debe usar para filtrar/asignar en el endpoint.

    - SUPER_ADMIN: puede pasar ?empresa_id= por query string para ver/editar una
      empresa puntual (ej. corregir un registro mal asignado). Si no lo manda,
      devuelve None (sin filtro = ve todas las empresas).
    - Cualquier otro rol: SIEMPRE devuelve el empresa_id de su propio usuario,
      sin excepcion. El parametro empresa_id de query (si lo mandan) se ignora
      por completo -- nunca se confia en lo que venga del cliente.
    """
    if usuario.rol == "SUPER_ADMIN":
        return empresa_id
    return usuario.empresa_id
