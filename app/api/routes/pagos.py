# Endpoints de pagos + lógica de segundo postor cuando el ganador no paga

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
from app.db.session import get_db
from app.db.models import Pago, Subasta, Oferta, Notificacion, Usuario
from app.api.routes.usuarios import obtener_usuario_actual

router = APIRouter(prefix="/pagos", tags=["pagos"])

# Límites de pago por tipo de categoría (en horas)
LIMITES_PAGO = {
    1: 48,   # artículos generales → 48 horas
    2: 72,   # vehículos           → 72 horas
    3: 168,  # inmuebles           → 7 días = 168 horas
}


# ─── Schemas Pydantic ─────────────────────────────────────────────────────────

class PagoCrear(BaseModel):
    """Datos para registrar un pago"""
    cve_subasta:          int
    metodo_pago:          str              # transferencia, debito, credito
    url_comprobante:      Optional[str] = None
    es_escalonado:        bool = False
    tipo_pago_escalonado: Optional[str] = None


class PagoRespuesta(BaseModel):
    id_pago:              int
    monto:                float
    fecha_realizacion:    Optional[datetime]
    fecha_limite:         datetime
    metodo_pago:          Optional[str]
    url_comprobante:      Optional[str]
    cve_status:           int
    cve_subasta:          int

    class Config:
        from_attributes = True


# ─── Funciones auxiliares ─────────────────────────────────────────────────────

async def calcular_fecha_limite(subasta: Subasta, db: AsyncSession) -> datetime:
    """
    Calcula la fecha límite de pago según el tipo de producto.
    Artículos generales: 48h, Vehículos: 72h, Inmuebles: 7 días.
    """
    from app.db.models import Producto, Vehiculo, Inmueble

    resultado = await db.execute(
        select(Producto).where(Producto.id_producto == subasta.cve_producto)
    )
    producto = resultado.scalar_one_or_none()

    # Determinar horas límite según categoría
    horas = LIMITES_PAGO.get(producto.cve_categoria, 48)
    return subasta.fecha_final + timedelta(hours=horas)


async def notificar_usuario(
    db: AsyncSession,
    id_usuario: int,
    descripcion: str,
    id_subasta: int,
    tipo: int = 1
):
    """Crea una notificación para un usuario."""
    notificacion = Notificacion(
        descripcion=descripcion,
        fecha_envio=datetime.utcnow(),
        leida=False,
        cve_usuario=id_usuario,
        cve_tipo_notificacion=tipo,
        cve_subasta=id_subasta
    )
    db.add(notificacion)


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/", response_model=PagoRespuesta, status_code=201)
async def registrar_pago(
    datos: PagoCrear,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    """
    Registra el pago del ganador de una subasta.
    Verifica que el usuario sea el ganador y que esté dentro del límite de tiempo.
    """
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

    # Verificar que el usuario es el ganador
    if subasta.cve_usuario_ganador != usuario_actual.id_usuario:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el ganador puede registrar el pago"
        )

    # Verificar que la subasta está cerrada (status 2)
    if subasta.cve_status != 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La subasta aún no ha cerrado"
        )

    # Calcular fecha límite según tipo de producto
    fecha_limite = await calcular_fecha_limite(subasta, db)

    # Verificar que no se pasó del límite de tiempo
    if datetime.utcnow() > fecha_limite:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El tiempo límite de pago ha vencido"
        )

    # Registrar el pago
    nuevo_pago = Pago(
        monto=subasta.precio_actual,
        fecha_realizacion=datetime.utcnow(),
        fecha_limite=fecha_limite,
        metodo_pago=datos.metodo_pago,
        url_comprobante=datos.url_comprobante,
        es_escalonado=datos.es_escalonado,
        tipo_pago_escalonado=datos.tipo_pago_escalonado,
        cve_status=2,       # completado
        cve_subasta=datos.cve_subasta
    )

    # Marcar subasta como pagada (status 3)
    subasta.cve_status = 3

    db.add(nuevo_pago)

    # Notificar al vendedor que recibió el pago
    resultado_producto = await db.execute(
        select(Usuario).join(
            Subasta, Subasta.cve_usuario_ganador == Usuario.id_usuario
        )
    )

    await notificar_usuario(
        db=db,
        id_usuario=usuario_actual.id_usuario,
        descripcion=f"Tu pago de ${subasta.precio_actual:.2f} fue registrado correctamente.",
        id_subasta=datos.cve_subasta,
        tipo=2
    )

    await db.commit()
    await db.refresh(nuevo_pago)
    return nuevo_pago


@router.post("/verificar-vencidos")
async def verificar_pagos_vencidos(
    db: AsyncSession = Depends(get_db)
):
    """
    Verifica subastas cerradas cuyo plazo de pago venció.
    Si el ganador no pagó → ofrecer al segundo postor.
    Si el segundo postor tampoco pagó → subasta desierta.
    Normalmente esta función la llama Celery automáticamente.
    """
    # Buscar subastas cerradas sin pago (status 2 = cerrada)
    resultado = await db.execute(
        select(Subasta).where(Subasta.cve_status == 2)
    )
    subastas_cerradas = resultado.scalars().all()

    procesadas = 0

    for subasta in subastas_cerradas:
        # Verificar si ya existe un pago
        resultado_pago = await db.execute(
            select(Pago).where(Pago.cve_subasta == subasta.id_subasta)
        )
        pago = resultado_pago.scalar_one_or_none()

        if pago:
            continue  # Ya tiene pago, saltar

        # Calcular fecha límite
        fecha_limite = await calcular_fecha_limite(subasta, db)

        # Si no venció el plazo, saltar
        if datetime.utcnow() <= fecha_limite:
            continue

        # ── El ganador no pagó a tiempo ──────────────────────────────────────

        if subasta.cve_segundo_postor:
            # Hay segundo postor → ofrecerle la subasta
            ganador_anterior = subasta.cve_usuario_ganador
            subasta.cve_usuario_ganador = subasta.cve_segundo_postor
            subasta.cve_segundo_postor  = None

            # Calcular nueva fecha límite para el segundo postor
            nueva_fecha_limite = datetime.utcnow() + timedelta(hours=48)

            # Crear registro de pago pendiente para el segundo postor
            pago_pendiente = Pago(
                monto=subasta.precio_actual,
                fecha_realizacion=None,
                fecha_limite=nueva_fecha_limite,
                cve_status=1,           # pendiente
                cve_subasta=subasta.id_subasta
            )
            db.add(pago_pendiente)

            # Notificar al segundo postor
            await notificar_usuario(
                db=db,
                id_usuario=subasta.cve_usuario_ganador,
                descripcion=(
                    f"¡Felicidades! El ganador anterior no realizó el pago. "
                    f"Ahora eres el ganador de la subasta #{subasta.id_subasta}. "
                    f"Tienes 48 horas para realizar el pago de ${subasta.precio_actual:.2f}."
                ),
                id_subasta=subasta.id_subasta,
                tipo=3
            )

        else:
            # No hay segundo postor → subasta desierta (status 4)
            subasta.cve_status = 4

            # Obtener al vendedor del producto
            resultado_producto = await db.execute(
                select(Usuario).join(
                    Subasta, Subasta.cve_producto == subasta.cve_producto
                )
            )

            # Notificar al vendedor que la subasta quedó desierta
            if subasta.cve_usuario_ganador:
                await notificar_usuario(
                    db=db,
                    id_usuario=subasta.cve_usuario_ganador,
                    descripcion=(
                        f"La subasta #{subasta.id_subasta} quedó desierta porque "
                        f"ningún postor realizó el pago. "
                        f"Puedes reactivarla con las mismas condiciones o modificarla."
                    ),
                    id_subasta=subasta.id_subasta,
                    tipo=4
                )

        procesadas += 1

    await db.commit()
    return {"procesadas": procesadas, "mensaje": "Verificación completada"}


@router.get("/subasta/{id_subasta}", response_model=PagoRespuesta)
async def obtener_pago_subasta(
    id_subasta: int,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    """Obtiene el pago asociado a una subasta."""
    resultado = await db.execute(
        select(Pago).where(Pago.cve_subasta == id_subasta)
    )
    pago = resultado.scalar_one_or_none()

    if not pago:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró pago para esta subasta"
        )

    return pago
