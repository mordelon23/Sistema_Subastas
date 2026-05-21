# Seguridad del sistema: hash de contraseñas y tokens JWT

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings

# Contexto para hash de contraseñas con bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hashear_contrasena(contrasena: str) -> str:
    """Convierte contraseña plana a hash bcrypt para guardar en BD."""
    return pwd_context.hash(contrasena)


def verificar_contrasena(contrasena_plana: str, contrasena_hash: str) -> bool:
    """Verifica que la contraseña plana coincide con el hash guardado."""
    return pwd_context.verify(contrasena_plana, contrasena_hash)


def crear_token_acceso(data: dict, expira_en: Optional[timedelta] = None) -> str:
    """
    Genera un JWT con los datos del usuario.
    El token expira en ACCESS_TOKEN_EXPIRE_MINUTES minutos.
    """
    datos = data.copy()

    # Calcular tiempo de expiración
    if expira_en:
        expira = datetime.utcnow() + expira_en
    else:
        expira = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    datos.update({"exp": expira})

    # Firmar el token con la clave secreta
    token = jwt.encode(
        datos,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return token


def verificar_token(token: str) -> Optional[dict]:
    """
    Decodifica y verifica un JWT.
    Retorna los datos si es válido, None si expiró o es inválido.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None
