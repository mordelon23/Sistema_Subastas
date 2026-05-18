# Maneja la conexión asíncrona a PostgreSQL
# Es el puente entre FastAPI y la base de datos

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

# Motor de conexión async — equivalente a "abrir el socket" a PostgreSQL
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,  # muestra las queries SQL en consola (útil para debug)
)

# Fábrica de sesiones — cada request HTTP obtiene su propia sesión
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Clase base para todos los modelos de la base de datos
class Base(DeclarativeBase):
    pass

# Dependencia que FastAPI inyecta en cada endpoint
async def get_db():
    """
    Genera una sesión de BD por cada request.
    La cierra automáticamente al terminar — como fclose() en C.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise