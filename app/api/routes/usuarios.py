# Endpoints de usuarios: registro, login y perfil

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from typing import Optional
from app.db.session import get_db
from app.db.models import Usuario, TipoUsuario
from app.core.security import hashear_contrasena, verificar_contrasena, crear_token_acceso

router = APIRouter(prefix="/usuarios", tags=["usuarios"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/usuarios/login")


# ─── Schemas Pydantic ─────────────────────────────────────────────────────────

class UsuarioRegistro(BaseModel):
    """Datos requeridos para registrar un nuevo usuario"""
    correo:           EmailStr
    contrasena:       str
    nombre:           str
    apellido_paterno: str
    apellido_materno: Optional[str] = None
    cve_tipo_usuario: int  # 1=Visitante, 2=Comprador/Vendedor


class UsuarioRespuesta(BaseModel):
    """Datos del usuario que se devuelven al cliente"""
    id_usuario:       int
    correo:           str
    nombre:           str
    apellido_paterno: str
    calificacion:     float
    activo:           bool

    class Config:
        from_attributes = True


class TokenRespuesta(BaseModel):
    """Token JWT que se devuelve al hacer login"""
    access_token: str
    token_type:   str


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/registro", response_model=UsuarioRespuesta, status_code=201)
async def registrar_usuario(
    datos: UsuarioRegistro,
    db: AsyncSession = Depends(get_db)
):
    """
    Registra un nuevo usuario en el sistema.
    Verifica que el correo no esté ya registrado.
    """
    # Verificar si el correo ya existe
    resultado = await db.execute(
        select(Usuario).where(Usuario.correo == datos.correo)
    )
    if resultado.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El correo ya está registrado"
        )

    # Crear usuario con contraseña hasheada
    nuevo_usuario = Usuario(
        correo=datos.correo,
        contrasena=hashear_contrasena(datos.contrasena),
        nombre=datos.nombre,
        apellido_paterno=datos.apellido_paterno,
        apellido_materno=datos.apellido_materno,
        cve_tipo_usuario=datos.cve_tipo_usuario,
        activo=True,
        suspendido=False,
        calificacion=0.0
    )

    db.add(nuevo_usuario)
    await db.commit()
    await db.refresh(nuevo_usuario)
    return nuevo_usuario


@router.post("/login", response_model=TokenRespuesta)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    Autentica al usuario y devuelve un token JWT.
    El username en el form es el correo del usuario.
    """
    # Buscar usuario por correo
    resultado = await db.execute(
        select(Usuario).where(Usuario.correo == form_data.username)
    )
    usuario = resultado.scalar_one_or_none()

    # Verificar existencia y contraseña
    if not usuario or not verificar_contrasena(form_data.password, usuario.contrasena):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verificar que la cuenta esté activa
    if not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cuenta desactivada"
        )

    # Verificar suspensión
    if usuario.suspendido:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cuenta suspendida temporalmente"
        )

    # Generar token JWT con el ID y tipo del usuario
    token = crear_token_acceso(data={
        "sub": str(usuario.id_usuario),
        "tipo": usuario.cve_tipo_usuario
    })

    return {"access_token": token, "token_type": "bearer"}


@router.get("/perfil/{id_usuario}", response_model=UsuarioRespuesta)
async def obtener_perfil(
    id_usuario: int,
    db: AsyncSession = Depends(get_db)
):
    """Obtiene el perfil público de un usuario."""
    resultado = await db.execute(
        select(Usuario).where(Usuario.id_usuario == id_usuario)
    )
    usuario = resultado.scalar_one_or_none()

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )

    return usuario


async def obtener_usuario_actual(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> Usuario:
    """
    Dependencia que extrae el usuario del token JWT.
    Se usa en endpoints que requieren autenticación.
    """
    from app.core.security import verificar_token

    payload = verificar_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    id_usuario = int(payload.get("sub"))
    resultado = await db.execute(
        select(Usuario).where(Usuario.id_usuario == id_usuario)
    )
    usuario = resultado.scalar_one_or_none()

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )

    return usuario
