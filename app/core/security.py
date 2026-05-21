# Seguridad del sistema: hash de contraseñas y tokens JWT

from datetime import datetime, timedelta
from typing import Optional
import bcrypt
from jose import JWTError, jwt
from app.core.config import settings


def hashear_contrasena(contrasena: str) -> str:
    """Convierte contraseña plana a hash bcrypt para guardar en BD."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(contrasena.encode("utf-8"), salt).decode("utf-8")


def verificar_contrasena(contrasena_plana: str, contrasena_hash: str) -> bool:
    """Verifica que la contraseña plana coincide con el hash guardado."""
    return bcrypt.checkpw(
        contrasena_plana.encode("utf-8"),
        contrasena_hash.encode("utf-8")
    )


def crear_token_acceso(data: dict, expira_en: Optional[timedelta] = None) -> str:
    """Genera un JWT con los datos del usuario."""
    datos = data.copy()
    if expira_en:
        expira = datetime.utcnow() + expira_en
    else:
        expira = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    datos.update({"exp": expira})
    return jwt.encode(datos, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verificar_token(token: str) -> Optional[dict]:
    """Decodifica y verifica un JWT."""
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None