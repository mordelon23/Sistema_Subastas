# Endpoints de subastas: crear, listar, ver y ofertar

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.db.session import get_db
from app.db.models import Subasta, Producto, Usuario, StatusSubasta
from app.api.routes.usuarios import obtener_usuario_actual

router = APIRouter(prefix="/subastas", tags=["subastas"])


# ─── Schemas Pydantic ─────────────────────────────────────────────────────────

class SubastaCrear(BaseModel):
    """Datos para crear una nueva subasta"""
    precio_inicial:   float
    incremento:       float
    fecha_inicio:     datetime
    fecha_final:      datetime
    cantidad:         int = 1
    cve_tipo_subasta: int
    cve_producto:     int


class SubastaRespuesta(BaseModel):
    """Datos de subasta que se devuelven al cliente"""
    id_subasta:       int
    precio_inicial:   float
    precio_actual:    float
    incremento:       float
    fecha_inicio:     datetime
    fecha_final:      datetime
    cantidad:         int
    cve_tipo_subasta: int
    cve_producto:     int
    cve_status:       int

    class Config:
        from_attributes = True


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[SubastaRespuesta])
async def listar_subastas(
    db: AsyncSession = Depends(get_db)
):
    """
    Lista todas las subastas activas.
    Accesible para visitantes y compradores.
    """
    resultado = await db.execute(
        select(Subasta).where(Subasta.cve_status == 1)  # 1 = activa
    )
    return resultado.scalars().all()


@router.get("/{id_subasta}", response_model=SubastaRespuesta)
async def obtener_subasta(
    id_subasta: int,
    db: AsyncSession = Depends(get_db)
):
    """Obtiene el detalle de una subasta por su ID."""
    resultado = await db.execute(
        select(Subasta).where(Subasta.id_subasta == id_subasta)
    )
    subasta = resultado.scalar_one_or_none()

    if not subasta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subasta no encontrada"
        )

    return subasta


@router.post("/", response_model=SubastaRespuesta, status_code=201)
async def crear_subasta(
    datos: SubastaCrear,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    """
    Crea una nueva subasta.
    Solo usuarios tipo comprador/vendedor pueden crear subastas.
    """
    # Solo tipo 2 (comprador/vendedor) puede crear subastas
    if usuario_actual.cve_tipo_usuario != 2:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo compradores/vendedores pueden crear subastas"
        )

    # Verificar que el producto existe y pertenece al usuario
    resultado = await db.execute(
        select(Producto).where(
            Producto.id_producto == datos.cve_producto,
            Producto.cve_usuario == usuario_actual.id_usuario
        )
    )
    producto = resultado.scalar_one_or_none()

    if not producto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado o no te pertenece"
        )

    # Validar fechas
    if datos.fecha_final <= datos.fecha_inicio:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La fecha final debe ser posterior a la fecha de inicio"
        )

    # Crear la subasta con status inicial = 1 (activa)
    nueva_subasta = Subasta(
        precio_inicial=datos.precio_inicial,
        precio_actual=datos.precio_inicial,   # arranca igual al precio inicial
        incremento=datos.incremento,
        fecha_inicio=datos.fecha_inicio,
        fecha_final=datos.fecha_final,
        cantidad=datos.cantidad,
        cve_tipo_subasta=datos.cve_tipo_subasta,
        cve_producto=datos.cve_producto,
        cve_status=1  # activa
    )

    db.add(nueva_subasta)
    await db.commit()
    await db.refresh(nueva_subasta)
    return nueva_subasta
