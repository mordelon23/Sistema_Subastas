# Endpoints de ofertas: realizar y listar ofertas de una subasta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List
from datetime import datetime
from app.db.session import get_db
from app.db.models import Oferta, Subasta, Usuario
from app.api.routes.usuarios import obtener_usuario_actual

router = APIRouter(prefix="/ofertas", tags=["ofertas"])


# ─── Schemas Pydantic ─────────────────────────────────────────────────────────

class OfertaCrear(BaseModel):
    """Datos para realizar una oferta"""
    monto:       float
    cve_subasta: int


class OfertaRespuesta(BaseModel):
    """Datos de la oferta que se devuelven al cliente"""
    id_oferta:   int
    monto:       float
    fecha:       datetime
    cve_usuario: int
    cve_subasta: int

    class Config:
        from_attributes = True


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/", response_model=OfertaRespuesta, status_code=201)
async def realizar_oferta(
    datos: OfertaCrear,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    """
    Registra una oferta de un comprador en una subasta.
    Valida que la oferta supere la actual y que la subasta esté activa.
    Una vez registrada, la oferta NO puede cancelarse.
    """
    # Solo tipo 2 (comprador/vendedor) puede ofertar
    if usuario_actual.cve_tipo_usuario != 2:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo compradores pueden realizar ofertas"
        )

    # Obtener la subasta
    resultado = await db.execute(
        select(Subasta).where(Subasta.id_subasta == datos.cve_subasta)
    )
    subasta = resultado.scalar_one_or_none()

    if not subasta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subasta no encontrada"
        )

    # Verificar que la subasta esté activa
    if subasta.cve_status != 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La subasta no está activa"
        )

    # Verificar que no haya terminado el tiempo
    if datetime.utcnow() > subasta.fecha_final:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La subasta ya finalizó"
        )

    # Verificar que la oferta supere el precio actual + incremento mínimo
    monto_minimo = subasta.precio_actual + subasta.incremento
    if datos.monto < monto_minimo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La oferta debe ser al menos ${monto_minimo:.2f}"
        )

    # Registrar la oferta
    nueva_oferta = Oferta(
        monto=datos.monto,
        fecha=datetime.utcnow(),
        cve_usuario=usuario_actual.id_usuario,
        cve_subasta=datos.cve_subasta
    )

    # Actualizar precio actual de la subasta
    subasta.precio_actual = datos.monto

    db.add(nueva_oferta)
    await db.commit()
    await db.refresh(nueva_oferta)
    return nueva_oferta


@router.get("/subasta/{id_subasta}", response_model=List[OfertaRespuesta])
async def listar_ofertas_subasta(
    id_subasta: int,
    db: AsyncSession = Depends(get_db)
):
    """Lista todas las ofertas de una subasta ordenadas de mayor a menor."""
    resultado = await db.execute(
        select(Oferta)
        .where(Oferta.cve_subasta == id_subasta)
        .order_by(Oferta.monto.desc())
    )
    return resultado.scalars().all()
