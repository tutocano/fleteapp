from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import auth
from app.database import get_db
from app.models import models
from app.schemas import schemas

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=schemas.LoginResponse)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    usuario = db.query(models.Usuario).filter(models.Usuario.email == payload.email).first()
    if not usuario or not usuario.activo or not auth.verify_password(payload.password, usuario.password_hash):
        raise HTTPException(status_code=401, detail="Correo o contrasena incorrectos")
    token = auth.crear_token(usuario)
    return schemas.LoginResponse(access_token=token, usuario=usuario)


@router.get("/me", response_model=schemas.UsuarioOut)
def me(usuario: models.Usuario = Depends(auth.get_current_user)):
    return usuario
