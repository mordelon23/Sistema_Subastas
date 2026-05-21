# Endpoints de productos: crear, listar, ver, actualizar y eliminar

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List
from app.db.session import get_db
from app.db.models import Producto, Vehiculo, Inmueble, FotoProducto, Usuario
from app.api.routes.usuarios import obtener_usuario_actual

router = APIRouter(prefix="/productos", tags=["productos"])


# ─── Schemas Pydantic ─────────────────────────────────────────────────────────

class VehiculoCrear(BaseModel):
    marca:             str
    modelo:            str
    anio:              int
    kilometraje:       Optional[float] = None
    numero_serie:      Optional[str]   = None
    condicion_mecanica: Optional[str]  = None
    url_documentacion: Optional[str]   = None


class InmuebleCrear(BaseModel):
    tipo_propiedad:        Optional[str]   = None
    superficie_terreno:    Optional[float] = None
    superficie_construida: Optional[float] = None
    no_habitaciones:       Optional[int]   = None
    ubicacion_detallada:   Optional[str]   = None
    url_documentacion:     Optional[str]   = None


class ProductoCrear(BaseModel):
    """Datos para crear un producto — puede incluir datos de vehículo o inmueble"""
    nombre:        str
    descripcion:   Optional[str] = None
    ubicacion:     Optional[str] = None
    cve_categoria: int
    cve_condicion: int
    vehiculo:      Optional[VehiculoCrear]  = None
    inmueble:      Optional[InmuebleCrear]  = None


class ProductoRespuesta(BaseModel):
    id_producto:   int
    nombre:        str
    descripcion:   Optional[str]
    ubicacion:     Optional[str]
    cve_categoria: int
    cve_condicion: int
    cve_usuario:   int
    cve_status:    int

    class Config:
        from_attributes = True


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[ProductoRespuesta])
async def listar_productos(
    cve_categoria: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Lista productos disponibles.
    Visitantes y compradores pueden ver el catálogo.
    Filtra por categoría si se proporciona.
    """
    query = select(Producto).where(Producto.cve_status == 1)  # 1 = disponible

    if cve_categoria:
        query = query.where(Producto.cve_categoria == cve_categoria)

    resultado = await db.execute(query)
    return resultado.scalars().all()


@router.get("/{id_producto}", response_model=ProductoRespuesta)
async def obtener_producto(
    id_producto: int,
    db: AsyncSession = Depends(get_db)
):
    """Obtiene el detalle de un producto por su ID."""
    resultado = await db.execute(
        select(Producto).where(Producto.id_producto == id_producto)
    )
    producto = resultado.scalar_one_or_none()

    if not producto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado"
        )

    return producto


@router.post("/", response_model=ProductoRespuesta, status_code=201)
async def crear_producto(
    datos: ProductoCrear,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    """
    Crea un nuevo producto para subastar.
    Solo compradores/vendedores pueden publicar productos.
    Si incluye datos de vehículo o inmueble, los registra también.
    """
    # Solo tipo 2 puede publicar productos
    if usuario_actual.cve_tipo_usuario != 2:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo compradores/vendedores pueden publicar productos"
        )

    # Crear el producto base
    nuevo_producto = Producto(
        nombre=datos.nombre,
        descripcion=datos.descripcion,
        ubicacion=datos.ubicacion,
        cve_categoria=datos.cve_categoria,
        cve_condicion=datos.cve_condicion,
        cve_usuario=usuario_actual.id_usuario,
        cve_status=1  # disponible — pendiente de validación admin
    )

    db.add(nuevo_producto)
    await db.flush()  # obtener el id_producto antes del commit

    # Si es vehículo, registrar datos adicionales
    if datos.vehiculo:
        vehiculo = Vehiculo(
            marca=datos.vehiculo.marca,
            modelo=datos.vehiculo.modelo,
            anio=datos.vehiculo.anio,
            kilometraje=datos.vehiculo.kilometraje,
            numero_serie=datos.vehiculo.numero_serie,
            condicion_mecanica=datos.vehiculo.condicion_mecanica,
            url_documentacion=datos.vehiculo.url_documentacion,
            cve_producto=nuevo_producto.id_producto
        )
        db.add(vehiculo)

    # Si es inmueble, registrar datos adicionales
    if datos.inmueble:
        inmueble = Inmueble(
            tipo_propiedad=datos.inmueble.tipo_propiedad,
            superficie_terreno=datos.inmueble.superficie_terreno,
            superficie_construida=datos.inmueble.superficie_construida,
            no_habitaciones=datos.inmueble.no_habitaciones,
            ubicacion_detallada=datos.inmueble.ubicacion_detallada,
            url_documentacion=datos.inmueble.url_documentacion,
            cve_producto=nuevo_producto.id_producto
        )
        db.add(inmueble)

    await db.commit()
    await db.refresh(nuevo_producto)
    return nuevo_producto


@router.put("/{id_producto}", response_model=ProductoRespuesta)
async def actualizar_producto(
    id_producto: int,
    datos: ProductoCrear,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    """
    Actualiza un producto.
    Solo el dueño puede modificarlo y solo si no tiene subasta activa.
    """
    resultado = await db.execute(
        select(Producto).where(
            Producto.id_producto == id_producto,
            Producto.cve_usuario == usuario_actual.id_usuario
        )
    )
    producto = resultado.scalar_one_or_none()

    if not producto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado o no te pertenece"
        )

    # Actualizar campos
    producto.nombre      = datos.nombre
    producto.descripcion = datos.descripcion
    producto.ubicacion   = datos.ubicacion

    await db.commit()
    await db.refresh(producto)
    return producto


@router.delete("/{id_producto}", status_code=204)
async def eliminar_producto(
    id_producto: int,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    """
    Elimina un producto.
    Solo el dueño puede eliminarlo y solo si no tiene subasta activa.
    """
    resultado = await db.execute(
        select(Producto).where(
            Producto.id_producto == id_producto,
            Producto.cve_usuario == usuario_actual.id_usuario
        )
    )
    producto = resultado.scalar_one_or_none()

    if not producto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado o no te pertenece"
        )

    await db.delete(producto)
    await db.commit()


@router.post("/{id_producto}/fotos", status_code=201)
async def agregar_foto(
    id_producto: int,
    url: str,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    """Agrega una foto a un producto del usuario."""
    resultado = await db.execute(
        select(Producto).where(
            Producto.id_producto == id_producto,
            Producto.cve_usuario == usuario_actual.id_usuario
        )
    )
    producto = resultado.scalar_one_or_none()

    if not producto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado o no te pertenece"
        )

    foto = FotoProducto(url=url, cve_producto=id_producto)
    db.add(foto)
    await db.commit()

    return {"mensaje": "Foto agregada correctamente"}
