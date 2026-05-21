# Modelos de la base de datos del sistema de subastas
# Cada clase representa una tabla en PostgreSQL

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean,
    DateTime, ForeignKey, Text
)
from sqlalchemy.orm import relationship
from app.db.session import Base


# ─── Tablas de catálogo ───────────────────────────────────────────────────────

class TipoUsuario(Base):
    """Tipos de usuario: comprador/vendedor, visitante"""
    __tablename__ = "tipo_usuario"

    id_tipo_usuario = Column(Integer, primary_key=True, index=True)
    descripcion     = Column(String(50), nullable=False)

    usuarios = relationship("Usuario", back_populates="tipo_usuario")


class Categoria(Base):
    """Categorías de productos: electrónicos, vehículos, inmuebles, etc."""
    __tablename__ = "categoria"

    id_categoria = Column(Integer, primary_key=True, index=True)
    descripcion  = Column(String(100), nullable=False)

    productos = relationship("Producto", back_populates="categoria")


class Condicion(Base):
    """Condición del producto: nuevo, usado, reacondicionado"""
    __tablename__ = "condicion"

    id_condicion = Column(Integer, primary_key=True, index=True)
    descripcion  = Column(String(50), nullable=False)

    productos = relationship("Producto", back_populates="condicion")


class StatusProducto(Base):
    """Estado del producto: disponible, en subasta, vendido"""
    __tablename__ = "status_producto"

    id_status   = Column(Integer, primary_key=True, index=True)
    descripcion = Column(String(50), nullable=False)

    productos = relationship("Producto", back_populates="status")


class TipoSubasta(Base):
    """Tipo de subasta: inglesa, holandesa, sellada"""
    __tablename__ = "tipo_subasta"

    id_tipo_subasta = Column(Integer, primary_key=True, index=True)
    descripcion     = Column(String(100), nullable=False)

    subastas = relationship("Subasta", back_populates="tipo_subasta")


class StatusSubasta(Base):
    """Estado de la subasta: activa, cerrada, cancelada, desierta"""
    __tablename__ = "status_subasta"

    id_status   = Column(Integer, primary_key=True, index=True)
    descripcion = Column(String(50), nullable=False)

    subastas = relationship("Subasta", back_populates="status")


class StatusPago(Base):
    """Estado del pago: pendiente, completado, fallido, vencido"""
    __tablename__ = "status_pago"

    id_status   = Column(Integer, primary_key=True, index=True)
    descripcion = Column(String(50), nullable=False)

    pagos = relationship("Pago", back_populates="status")


class TipoNotificacion(Base):
    """Tipo de notificación: nueva oferta, superado, ganador, etc."""
    __tablename__ = "tipo_notificacion"

    id_tipo_notificacion = Column(Integer, primary_key=True, index=True)
    descripcion          = Column(String(100), nullable=False)

    notificaciones = relationship("Notificacion", back_populates="tipo_notificacion")


# ─── Usuario ──────────────────────────────────────────────────────────────────

class Usuario(Base):
    """Usuario del sistema — puede ser comprador/vendedor o visitante"""
    __tablename__ = "usuario"

    id_usuario        = Column(Integer, primary_key=True, index=True)
    correo            = Column(String(150), unique=True, nullable=False, index=True)
    contrasena        = Column(String(255), nullable=False)   # hash bcrypt
    nombre            = Column(String(100), nullable=False)
    apellido_paterno  = Column(String(100), nullable=False)
    apellido_materno  = Column(String(100), nullable=True)
    calificacion      = Column(Float, default=0.0)            # promedio calculado
    activo            = Column(Boolean, default=True)
    suspendido        = Column(Boolean, default=False)        # por incumplimiento
    fecha_suspension  = Column(DateTime, nullable=True)
    cve_tipo_usuario  = Column(Integer, ForeignKey("tipo_usuario.id_tipo_usuario"))

    # Relaciones
    tipo_usuario   = relationship("TipoUsuario", back_populates="usuarios")
    productos      = relationship("Producto", back_populates="usuario")
    ofertas        = relationship("Oferta", back_populates="usuario")
    notificaciones = relationship("Notificacion", back_populates="usuario")
    metodos_envio  = relationship("MetodoEnvio", back_populates="usuario")
    calificaciones_recibidas = relationship(
        "Calificacion",
        foreign_keys="Calificacion.cve_usuario_calificado",
        back_populates="usuario_calificado"
    )
    calificaciones_dadas = relationship(
        "Calificacion",
        foreign_keys="Calificacion.cve_usuario_calificador",
        back_populates="usuario_calificador"
    )


class MetodoEnvio(Base):
    """Métodos de envío disponibles del vendedor"""
    __tablename__ = "metodo_envio"

    id_metodo_envio = Column(Integer, primary_key=True, index=True)
    descripcion     = Column(String(150), nullable=False)
    cve_usuario     = Column(Integer, ForeignKey("usuario.id_usuario"))

    usuario = relationship("Usuario", back_populates="metodos_envio")


# ─── Producto ─────────────────────────────────────────────────────────────────

class Producto(Base):
    """Producto que se pone en subasta"""
    __tablename__ = "producto"

    id_producto   = Column(Integer, primary_key=True, index=True)
    nombre        = Column(String(200), nullable=False)
    descripcion   = Column(Text, nullable=True)
    ubicacion     = Column(String(200), nullable=True)
    cve_categoria = Column(Integer, ForeignKey("categoria.id_categoria"))
    cve_condicion = Column(Integer, ForeignKey("condicion.id_condicion"))
    cve_usuario   = Column(Integer, ForeignKey("usuario.id_usuario"))
    cve_status    = Column(Integer, ForeignKey("status_producto.id_status"))

    # Relaciones
    categoria = relationship("Categoria", back_populates="productos")
    condicion = relationship("Condicion", back_populates="productos")
    usuario   = relationship("Usuario", back_populates="productos")
    status    = relationship("StatusProducto", back_populates="productos")
    fotos     = relationship("FotoProducto", back_populates="producto")
    vehiculo  = relationship("Vehiculo", back_populates="producto", uselist=False)
    inmueble  = relationship("Inmueble", back_populates="producto", uselist=False)
    subastas  = relationship("Subasta", back_populates="producto")


class FotoProducto(Base):
    """Fotos asociadas a un producto"""
    __tablename__ = "foto_producto"

    id_foto      = Column(Integer, primary_key=True, index=True)
    url          = Column(String(500), nullable=False)
    cve_producto = Column(Integer, ForeignKey("producto.id_producto"))

    producto = relationship("Producto", back_populates="fotos")


class Vehiculo(Base):
    """Datos específicos de vehículos"""
    __tablename__ = "vehiculo"

    id_vehiculo       = Column(Integer, primary_key=True, index=True)
    marca             = Column(String(100), nullable=False)
    modelo            = Column(String(100), nullable=False)
    anio              = Column(Integer, nullable=False)
    kilometraje       = Column(Float, nullable=True)
    numero_serie      = Column(String(100), nullable=True)
    condicion_mecanica = Column(Text, nullable=True)
    url_documentacion = Column(String(500), nullable=True)
    cve_producto      = Column(Integer, ForeignKey("producto.id_producto"), unique=True)

    producto = relationship("Producto", back_populates="vehiculo")


class Inmueble(Base):
    """Datos específicos de inmuebles"""
    __tablename__ = "inmueble"

    id_inmueble            = Column(Integer, primary_key=True, index=True)
    tipo_propiedad         = Column(String(100), nullable=True)
    superficie_terreno     = Column(Float, nullable=True)
    superficie_construida  = Column(Float, nullable=True)
    no_habitaciones        = Column(Integer, nullable=True)
    ubicacion_detallada    = Column(Text, nullable=True)
    url_documentacion      = Column(String(500), nullable=True)
    cve_producto           = Column(Integer, ForeignKey("producto.id_producto"), unique=True)

    producto = relationship("Producto", back_populates="inmueble")


# ─── Subasta ──────────────────────────────────────────────────────────────────

class Subasta(Base):
    """Subasta — núcleo del sistema"""
    __tablename__ = "subasta"

    id_subasta           = Column(Integer, primary_key=True, index=True)
    precio_inicial       = Column(Float, nullable=False)
    precio_actual        = Column(Float, nullable=False)
    incremento           = Column(Float, nullable=False)  # mínimo por oferta
    fecha_inicio         = Column(DateTime, nullable=False)
    fecha_final          = Column(DateTime, nullable=False)
    cantidad             = Column(Integer, default=1)
    cve_tipo_subasta     = Column(Integer, ForeignKey("tipo_subasta.id_tipo_subasta"))
    cve_producto         = Column(Integer, ForeignKey("producto.id_producto"))
    cve_status           = Column(Integer, ForeignKey("status_subasta.id_status"))
    cve_usuario_ganador  = Column(Integer, ForeignKey("usuario.id_usuario"), nullable=True)
    cve_segundo_postor   = Column(Integer, ForeignKey("usuario.id_usuario"), nullable=True)

    # Relaciones
    tipo_subasta    = relationship("TipoSubasta", back_populates="subastas")
    producto        = relationship("Producto", back_populates="subastas")
    status          = relationship("StatusSubasta", back_populates="subastas")
    usuario_ganador = relationship("Usuario", foreign_keys=[cve_usuario_ganador])
    segundo_postor  = relationship("Usuario", foreign_keys=[cve_segundo_postor])
    ofertas         = relationship("Oferta", back_populates="subasta")
    pagos           = relationship("Pago", back_populates="subasta")
    calificaciones  = relationship("Calificacion", back_populates="subasta")
    notificaciones  = relationship("Notificacion", back_populates="subasta")
    confirmacion_entrega = relationship("ConfirmacionEntrega", back_populates="subasta", uselist=False)


# ─── Oferta ───────────────────────────────────────────────────────────────────

class Oferta(Base):
    """Oferta realizada por un comprador en una subasta"""
    __tablename__ = "oferta"

    id_oferta   = Column(Integer, primary_key=True, index=True)
    fecha       = Column(DateTime, default=datetime.utcnow, nullable=False)
    monto       = Column(Float, nullable=False)
    cve_usuario = Column(Integer, ForeignKey("usuario.id_usuario"))
    cve_subasta = Column(Integer, ForeignKey("subasta.id_subasta"))

    usuario = relationship("Usuario", back_populates="ofertas")
    subasta = relationship("Subasta", back_populates="ofertas")
    notificaciones = relationship("Notificacion", back_populates="oferta")


# ─── Pago ─────────────────────────────────────────────────────────────────────

class Pago(Base):
    """Pago realizado al cerrar una subasta"""
    __tablename__ = "pago"

    id_pago               = Column(Integer, primary_key=True, index=True)
    monto                 = Column(Float, nullable=False)
    fecha_realizacion     = Column(DateTime, nullable=True)
    fecha_limite          = Column(DateTime, nullable=False)
    url_comprobante       = Column(String(500), nullable=True)   # imagen de comprobante
    metodo_pago           = Column(String(50), nullable=True)    # transferencia/debito/credito
    es_escalonado         = Column(Boolean, default=False)       # solo inmuebles
    tipo_pago_escalonado  = Column(String(100), nullable=True)
    cve_status            = Column(Integer, ForeignKey("status_pago.id_status"))
    cve_subasta           = Column(Integer, ForeignKey("subasta.id_subasta"))

    status  = relationship("StatusPago", back_populates="pagos")
    subasta = relationship("Subasta", back_populates="pagos")


# ─── Confirmación de entrega ──────────────────────────────────────────────────

class ConfirmacionEntrega(Base):
    """Confirmación de entrega entre vendedor y comprador"""
    __tablename__ = "confirmacion_entrega"

    id_confirmacion           = Column(Integer, primary_key=True, index=True)
    url_imagen_envio          = Column(String(500), nullable=True)  # foto del vendedor
    url_imagen_recepcion      = Column(String(500), nullable=True)  # foto del comprador
    fecha_envio_confirmada    = Column(DateTime, nullable=True)
    fecha_recepcion_confirmada = Column(DateTime, nullable=True)
    cve_subasta               = Column(Integer, ForeignKey("subasta.id_subasta"), unique=True)

    subasta = relationship("Subasta", back_populates="confirmacion_entrega")


# ─── Calificación ─────────────────────────────────────────────────────────────

class Calificacion(Base):
    """Calificación mutua entre comprador y vendedor (1 a 5 estrellas)"""
    __tablename__ = "calificacion"

    id_calificacion         = Column(Integer, primary_key=True, index=True)
    calificacion            = Column(Float, nullable=False)   # 1.0 a 5.0
    comentario              = Column(Text, nullable=True)
    fecha                   = Column(DateTime, default=datetime.utcnow)
    cve_usuario_calificado  = Column(Integer, ForeignKey("usuario.id_usuario"))
    cve_usuario_calificador = Column(Integer, ForeignKey("usuario.id_usuario"))
    cve_subasta             = Column(Integer, ForeignKey("subasta.id_subasta"))

    usuario_calificado  = relationship(
        "Usuario",
        foreign_keys=[cve_usuario_calificado],
        back_populates="calificaciones_recibidas"
    )
    usuario_calificador = relationship(
        "Usuario",
        foreign_keys=[cve_usuario_calificador],
        back_populates="calificaciones_dadas"
    )
    subasta = relationship("Subasta", back_populates="calificaciones")


# ─── Notificación ─────────────────────────────────────────────────────────────

class Notificacion(Base):
    """Notificación enviada a un usuario"""
    __tablename__ = "notificacion"

    id_notificacion       = Column(Integer, primary_key=True, index=True)
    descripcion           = Column(Text, nullable=False)
    fecha_envio           = Column(DateTime, default=datetime.utcnow)
    leida                 = Column(Boolean, default=False)
    cve_usuario           = Column(Integer, ForeignKey("usuario.id_usuario"))
    cve_tipo_notificacion = Column(Integer, ForeignKey("tipo_notificacion.id_tipo_notificacion"))
    cve_oferta            = Column(Integer, ForeignKey("oferta.id_oferta"), nullable=True)
    cve_subasta           = Column(Integer, ForeignKey("subasta.id_subasta"), nullable=True)

    usuario           = relationship("Usuario", back_populates="notificaciones")
    tipo_notificacion = relationship("TipoNotificacion", back_populates="notificaciones")
    subasta           = relationship("Subasta", back_populates="notificaciones")
    oferta            = relationship("Oferta", back_populates="notificaciones")
