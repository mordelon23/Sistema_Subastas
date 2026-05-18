# Configuración central del sistema de subastas
# Lee las variables del archivo .env y las expone al resto de la app

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # URL de conexión a PostgreSQL
    DATABASE_URL: str
    
    # URL de conexión a Redis
    REDIS_URL: str
    
    # Clave secreta para firmar los tokens JWT
    SECRET_KEY: str
    
    # Algoritmo de encriptación para JWT
    ALGORITHM: str = "HS256"
    
    # Minutos que dura el token de sesión
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        # Le dice a Pydantic que lea el archivo .env
        env_file = ".env"

# Instancia global que usa toda la app
settings = Settings()