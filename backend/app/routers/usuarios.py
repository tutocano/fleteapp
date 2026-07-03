from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import auth
from app.database import get_db
from app.models import models
from app.schemas import schemas

# Gestion de usuarios: exclusivamente SUPER_ADMIN (ver plan v4, seccion 2).
# Los demas roles no pueden crear ni editar otros usuarios, ni siquiera los de
# su propia empresa.
router = APIRouter(prefix="/usuarios", tags=["Usuario"])


def _validar_rol_y_empresa(db: Session, rol: str, empresa_id):
    if rol not in models.ROLES_VALIDOS:
        raise HTTPException(
            status_code=400, detail=f"Rol invalido. Debe ser uno de: {models.ROLES_VALIDOS}"
        )
    if rol == "SUPER_ADMIN":
        return None  # SUPER_ADMIN no pertenece a ninguna empresa
    if not empresa_id:
        raise HTTPException(
            status_code=400, detail=f"El rol {rol} requiere asignar una empresa (empresa_id)"
        )
    empresa = db.query(models.Empresa).get(empresa_id)
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return empresa_id


@router.get("/", response_model=List[schemas.UsuarioOut])
def listar_usuarios(
    db: Session = Depends(get_db), usuario: models.Usuario = Depends(auth.require_role())
):
    return db.query(models.Usuario).order_by(models.Usuario.id).all()


@router.get("/{usuario_id}", response_model=schemas.UsuarioOut)
def obtener_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(auth.require_role()),
):
    obj = db.query(models.Usuario).get(usuario_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return obj


@router.post("/", response_model=schemas.UsuarioOut)
def crear_usuario(
    payload: schemas.UsuarioCreate,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(auth.require_role()),
):
    empresa_id = _validar_rol_y_empresa(db, payload.rol, payload.empresa_id)
    obj = models.Usuario(
        nombre=payload.nombre,
        email=payload.email,
        password_hash=auth.hash_password(payload.password),
        rol=payload.rol,
        empresa_id=empresa_id,
        activo=payload.activo,
    )
    db.add(obj)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Ya existe un usuario con ese correo")
    db.refresh(obj)
    return obj


@router.put("/{usuario_id}", response_model=schemas.UsuarioOut)
def actualizar_usuario(
    usuario_id: int,
    payload: schemas.UsuarioUpdate,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(auth.require_role()),
):
    obj = db.query(models.Usuario).get(usuario_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    nuevo_rol = payload.rol if payload.rol is not None else obj.rol
    nueva_empresa = payload.empresa_id if payload.empresa_id is not None else obj.empresa_id
    empresa_resuelta = _validar_rol_y_empresa(db, nuevo_rol, nueva_empresa)

    if payload.nombre is not None:
        obj.nombre = payload.nombre
    obj.rol = nuevo_rol
    obj.empresa_id = empresa_resuelta
    if payload.activo is not None:
        obj.activo = payload.activo
    if payload.password:
        obj.password_hash = auth.hash_password(payload.password)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Ya existe un usuario con ese correo")
    db.refresh(obj)
    return obj


@router.delete("/{usuario_id}")
def eliminar_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(auth.require_role()),
):
    if usuario_id == usuario.id:
        raise HTTPException(status_code=400, detail="No puedes eliminar tu propio usuario")
    obj = db.query(models.Usuario).get(usuario_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    db.delete(obj)
    db.commit()
    return {"ok": True}
