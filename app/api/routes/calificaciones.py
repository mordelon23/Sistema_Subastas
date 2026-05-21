# Endpoints de calificaciones: calificar mutuamente comprador y vendedor

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.db.session import get_db
from app.db.models import Calificacion, Subasta, Usuario
from app.api.routes.usuarios import obtener_usuario_actual

router = APIRouter(prefix="/calificaciones", tags=["calificaciones"])


# ─── Schemas Pydantic ─────────────────────────────────────────────────────────

class CalificacionCrear(BaseModel):
    """Datos para calificar a otro usuario"""
    calificacion:              float  # 1.0 a 5.0 estrellas
    comentario:                Optional[str] = None
    cve_usuario_calificado:    int
    cve_subasta:               int


class CalificacionRespuesta(BaseModel):
    id_calificacion:           int
    calificacion:              float
    comentario:                Optional[str]
    fecha:                     datetime
    cve_usuario_calificado:    int
    cve_usuario_calificador:   int
    cve_subasta:               int

    class Config:
        from_attributes = True


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/", response_model=CalificacionRespuesta, status_code=201)
async def crear_calificacion(
    datos: CalificacionCrear,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    """
    Califica a otro usuario después de una subasta.
    La calificación es de 1 a 5 estrellas.
    Solo participantes de la subasta pueden calificarse mutuamente.
    """
    # Validar rango de calificación
    if not (1.0 <= datos.calificacion <= 5.0):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La calificación debe estar entre 1.0 y 5.0"
        )

    # Verificar que la subasta existe y está cerrada o pagada
    resultado = await db.execute(
        select(Subasta).where(Subasta.id_subasta == datos.cve_subasta)
    )
    subasta = resultado.scalar_one_or_none()

    if not subasta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subasta no encontrada"
        )

    if subasta.cve_status not in [2, 3]:  # 2=cerrada, 3=pagada
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo puedes calificar en subastas finalizadas"
        )

    # Verificar que no se haya calificado ya en esta subasta
    resultado_existente = await db.execute(
        select(Calificacion).where(
            Calificacion.cve_subasta == datos.cve_subasta,
            Calificacion.cve_usuario_calificador == usuario_actual.id_usuario,
            Calificacion.cve_usuario_calificado == datos.cve_usuario_calificado
        )
    )
    if resultado_existente.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya calificaste a este usuario en esta subasta"
        )

    # Registrar calificación
    nueva_calificacion = Calificacion(
        calificacion=datos.calificacion,
        comentario=datos.comentario,
        fecha=datetime.utcnow(),
        cve_usuario_calificado=datos.cve_usuario_calificado,
        cve_usuario_calificador=usuario_actual.id_usuario,
        cve_subasta=datos.cve_subasta
    )
    db.add(nueva_calificacion)

    # Actualizar promedio de calificación del usuario calificado
    resultado_promedio = await db.execute(
        select(func.avg(Calificacion.calificacion)).where(
            Calificacion.cve_usuario_calificado == datos.cve_usuario_calificado
        )
    )
    promedio = resultado_promedio.scalar() or datos.calificacion

    resultado_usuario = await db.execute(
        select(Usuario).where(Usuario.id_usuario == datos.cve_usuario_calificado)
    )
    usuario_calificado = resultado_usuario.scalar_one_or_none()

    if usuario_calificado:
        usuario_calificado.calificacion = round(promedio, 2)

    await db.commit()
    await db.refresh(nueva_calificacion)
    return nueva_calificacion


@router.get("/usuario/{id_usuario}", response_model=List[CalificacionRespuesta])
async def listar_calificaciones_usuario(
    id_usuario: int,
    db: AsyncSession = Depends(get_db)
):
    """Lista todas las calificaciones recibidas por un usuario."""
    resultado = await db.execute(
        select(Calificacion).where(
            Calificacion.cve_usuario_calificado == id_usuario
        ).order_by(Calificacion.fecha.desc())
    )
    return resultado.scalars().all()
