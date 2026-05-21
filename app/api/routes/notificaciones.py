# Endpoints de notificaciones: listar y marcar como leídas

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.db.session import get_db
from app.db.models import Notificacion, Usuario
from app.api.routes.usuarios import obtener_usuario_actual

router = APIRouter(prefix="/notificaciones", tags=["notificaciones"])


# ─── Schemas Pydantic ─────────────────────────────────────────────────────────

class NotificacionRespuesta(BaseModel):
    id_notificacion:       int
    descripcion:           str
    fecha_envio:           datetime
    leida:                 bool
    cve_usuario:           int
    cve_tipo_notificacion: int
    cve_subasta:           Optional[int]
    cve_oferta:            Optional[int]

    class Config:
        from_attributes = True


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[NotificacionRespuesta])
async def listar_notificaciones(
    solo_no_leidas: bool = False,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    """
    Lista las notificaciones del usuario autenticado.
    Puede filtrar solo las no leídas con ?solo_no_leidas=true
    """
    query = select(Notificacion).where(
        Notificacion.cve_usuario == usuario_actual.id_usuario
    ).order_by(Notificacion.fecha_envio.desc())

    if solo_no_leidas:
        query = query.where(Notificacion.leida == False)

    resultado = await db.execute(query)
    return resultado.scalars().all()


@router.put("/{id_notificacion}/leer", status_code=200)
async def marcar_como_leida(
    id_notificacion: int,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    """Marca una notificación como leída."""
    resultado = await db.execute(
        select(Notificacion).where(
            Notificacion.id_notificacion == id_notificacion,
            Notificacion.cve_usuario == usuario_actual.id_usuario
        )
    )
    notificacion = resultado.scalar_one_or_none()

    if not notificacion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notificación no encontrada"
        )

    notificacion.leida = True
    await db.commit()

    return {"mensaje": "Notificación marcada como leída"}


@router.put("/leer-todas", status_code=200)
async def marcar_todas_como_leidas(
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    """Marca todas las notificaciones del usuario como leídas."""
    resultado = await db.execute(
        select(Notificacion).where(
            Notificacion.cve_usuario == usuario_actual.id_usuario,
            Notificacion.leida == False
        )
    )
    notificaciones = resultado.scalars().all()

    for notificacion in notificaciones:
        notificacion.leida = True

    await db.commit()

    return {"mensaje": f"{len(notificaciones)} notificaciones marcadas como leídas"}
