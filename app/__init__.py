# Agente de subastas: cierra subastas expiradas y determina ganadores

from celery import Celery
from datetime import datetime
from app.core.config import settings

# Configuración de Celery con Redis como broker
celery_app = Celery(
    "subastas",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

celery_app.conf.update(
    # Ejecutar tarea de cierre cada 60 segundos
    beat_schedule={
        "cerrar-subastas-expiradas": {
            "task": "app.agents.cerrar_subastas_expiradas",
            "schedule": 60.0,  # cada minuto
        },
    },
    timezone="America/Mexico_City"
)


@celery_app.task(name="app.agents.cerrar_subastas_expiradas")
def cerrar_subastas_expiradas():
    """
    Tarea automática que corre cada minuto.
    Busca subastas cuyo fecha_final ya pasó y las cierra,
    determinando al ganador y al segundo mejor postor.
    """
    import asyncio
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.ext.asyncio import async_sessionmaker
    from sqlalchemy import select
    from app.db.models import Subasta, Oferta

    async def _cerrar():
        engine = create_async_engine(settings.DATABASE_URL)
        AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession)

        async with AsyncSessionLocal() as db:
            # Buscar subastas activas que ya expiraron
            resultado = await db.execute(
                select(Subasta).where(
                    Subasta.cve_status == 1,            # activa
                    Subasta.fecha_final <= datetime.utcnow()
                )
            )
            subastas_expiradas = resultado.scalars().all()

            for subasta in subastas_expiradas:
                # Obtener las dos mejores ofertas
                resultado_ofertas = await db.execute(
                    select(Oferta)
                    .where(Oferta.cve_subasta == subasta.id_subasta)
                    .order_by(Oferta.monto.desc())
                    .limit(2)
                )
                ofertas = resultado_ofertas.scalars().all()

                if ofertas:
                    # Asignar ganador y segundo postor
                    subasta.cve_usuario_ganador = ofertas[0].cve_usuario
                    if len(ofertas) > 1:
                        subasta.cve_segundo_postor = ofertas[1].cve_usuario

                # Marcar subasta como cerrada (status 2)
                subasta.cve_status = 2

            await db.commit()
        await engine.dispose()

    asyncio.run(_cerrar())
