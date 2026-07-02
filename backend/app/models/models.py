from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base


class Empresa(Base):
    __tablename__ = "empresa"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(200), nullable=False)
    nit = Column(String(50))
    direccion = Column(String(300))
    telefono = Column(String(50))
    email = Column(String(150))
    creado_en = Column(DateTime, default=datetime.utcnow)

    centros = relationship("CentroDistribucion", back_populates="empresa")
    clientes = relationship("Cliente", back_populates="empresa")
    transportistas = relationship("Transportista", back_populates="empresa")


class CentroDistribucion(Base):
    __tablename__ = "centro_distribucion"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresa.id"), nullable=False)
    nombre = Column(String(200), nullable=False)
    codigo = Column(String(50), unique=True)
    latitud = Column(Float, nullable=False)
    longitud = Column(Float, nullable=False)
    direccion = Column(String(300))
    creado_en = Column(DateTime, default=datetime.utcnow)

    empresa = relationship("Empresa", back_populates="centros")


class TipoCliente(Base):
    __tablename__ = "tipo_cliente"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False, unique=True)
    descripcion = Column(String(300))


class ZonaGeografica(Base):
    __tablename__ = "zona_geografica"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(150), nullable=False)
    descripcion = Column(String(300))
    tarifa_zona = Column(Float, nullable=False, default=0)
    creado_en = Column(DateTime, default=datetime.utcnow)


class Cliente(Base):
    __tablename__ = "cliente"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresa.id"), nullable=False)
    tipo_cliente_id = Column(Integer, ForeignKey("tipo_cliente.id"))
    zona_geografica_id = Column(Integer, ForeignKey("zona_geografica.id"))
    nombre = Column(String(200), nullable=False)
    codigo = Column(String(50), unique=True)
    latitud = Column(Float, nullable=False)
    longitud = Column(Float, nullable=False)
    direccion = Column(String(300))
    canal = Column(String(100))
    creado_en = Column(DateTime, default=datetime.utcnow)

    empresa = relationship("Empresa", back_populates="clientes")
    tipo_cliente = relationship("TipoCliente")
    zona_geografica = relationship("ZonaGeografica")


class TipoCamion(Base):
    __tablename__ = "tipo_camion"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    capacidad_peso_kg = Column(Float, nullable=False)
    capacidad_volumen_m3 = Column(Float, nullable=False)


class Transportista(Base):
    __tablename__ = "transportista"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresa.id"), nullable=False)
    nombre = Column(String(200), nullable=False)
    nit = Column(String(50))
    contacto = Column(String(150))
    telefono = Column(String(50))
    creado_en = Column(DateTime, default=datetime.utcnow)

    empresa = relationship("Empresa", back_populates="transportistas")
    flota = relationship("Flota", back_populates="transportista")
    tarifas = relationship("TarifaTransportista", back_populates="transportista")


class Flota(Base):
    __tablename__ = "flota"

    id = Column(Integer, primary_key=True, index=True)
    transportista_id = Column(Integer, ForeignKey("transportista.id"), nullable=False)
    tipo_camion_id = Column(Integer, ForeignKey("tipo_camion.id"), nullable=False)
    placa = Column(String(20))
    descripcion = Column(String(200))
    activo = Column(Boolean, default=True)

    transportista = relationship("Transportista", back_populates="flota")
    tipo_camion = relationship("TipoCamion")


class MetodoTarifa(Base):
    __tablename__ = "metodo_tarifa"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(50), nullable=False, unique=True)
    nombre = Column(String(150), nullable=False)
    descripcion = Column(String(400))


class TarifaTransportista(Base):
    __tablename__ = "tarifa_transportista"

    id = Column(Integer, primary_key=True, index=True)
    transportista_id = Column(Integer, ForeignKey("transportista.id"), nullable=False)
    metodo_tarifa_id = Column(Integer, ForeignKey("metodo_tarifa.id"), nullable=False)
    nombre = Column(String(150), nullable=False)
    valor_unitario = Column(Float, nullable=False, default=0)
    unidad = Column(String(30))
    activo = Column(Boolean, default=True)
    creado_en = Column(DateTime, default=datetime.utcnow)

    transportista = relationship("Transportista", back_populates="tarifas")
    metodo_tarifa = relationship("MetodoTarifa")
    zonas_detalle = relationship(
        "TarifaZonaDetalle", back_populates="tarifa_transportista", cascade="all, delete-orphan"
    )


class TarifaZonaDetalle(Base):
    __tablename__ = "tarifa_zona_detalle"
    __table_args__ = (
        UniqueConstraint("tarifa_transportista_id", "zona_geografica_id", name="uq_tarifa_zona"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tarifa_transportista_id = Column(
        Integer, ForeignKey("tarifa_transportista.id"), nullable=False
    )
    zona_geografica_id = Column(Integer, ForeignKey("zona_geografica.id"), nullable=False)
    valor = Column(Float, nullable=False, default=0)

    tarifa_transportista = relationship("TarifaTransportista", back_populates="zonas_detalle")
    zona_geografica = relationship("ZonaGeografica")


class Producto(Base):
    __tablename__ = "producto"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(200), nullable=False)
    codigo = Column(String(50), unique=True)
    peso_unitario_kg = Column(Float, nullable=False)
    volumen_unitario_m3 = Column(Float, nullable=False)


class Ruta(Base):
    __tablename__ = "ruta"

    id = Column(Integer, primary_key=True, index=True)
    codigo_ruta = Column(String(50), nullable=False)
    es_planificada = Column(Boolean, nullable=False, default=True)
    ruta_planificada_id = Column(Integer, ForeignKey("ruta.id"), nullable=True)
    centro_distribucion_id = Column(
        Integer, ForeignKey("centro_distribucion.id"), nullable=False
    )
    transportista_id = Column(Integer, ForeignKey("transportista.id"), nullable=False)
    tarifa_transportista_id = Column(
        Integer, ForeignKey("tarifa_transportista.id"), nullable=False
    )
    tipo_camion_id = Column(Integer, ForeignKey("tipo_camion.id"), nullable=False)
    flota_id = Column(Integer, ForeignKey("flota.id"), nullable=True)
    fecha = Column(DateTime, default=datetime.utcnow)
    estado = Column(String(30), default="REGISTRADA")
    costo_flete_calculado = Column(Float, nullable=True)
    detalle_calculo = Column(JSON, nullable=True)
    creado_en = Column(DateTime, default=datetime.utcnow)

    centro_distribucion = relationship("CentroDistribucion")
    transportista = relationship("Transportista")
    tarifa_transportista = relationship("TarifaTransportista")
    tipo_camion = relationship("TipoCamion")
    flota = relationship("Flota")
    paradas = relationship(
        "ParadaRuta", back_populates="ruta", cascade="all, delete-orphan",
        order_by="ParadaRuta.secuencia",
    )
    ruta_ejecutada = relationship(
        "Ruta", remote_side=[id], backref="ruta_origen_planificada"
    )


class ParadaRuta(Base):
    __tablename__ = "parada_ruta"

    id = Column(Integer, primary_key=True, index=True)
    ruta_id = Column(Integer, ForeignKey("ruta.id"), nullable=False)
    cliente_id = Column(Integer, ForeignKey("cliente.id"), nullable=False)
    secuencia = Column(Integer, nullable=False)
    distancia_km_tramo = Column(Float, nullable=False, default=0)
    tiempo_transito_min_tramo = Column(Float, nullable=False, default=0)
    tiempo_servicio_min = Column(Float, nullable=False, default=0)
    hora_llegada_estimada = Column(DateTime, nullable=True)
    hora_llegada_real = Column(DateTime, nullable=True)

    ruta = relationship("Ruta", back_populates="paradas")
    cliente = relationship("Cliente")
    pedidos = relationship(
        "PedidoClienteRuta", back_populates="parada_ruta", cascade="all, delete-orphan"
    )


class PedidoClienteRuta(Base):
    __tablename__ = "pedido_cliente_ruta"

    id = Column(Integer, primary_key=True, index=True)
    parada_ruta_id = Column(Integer, ForeignKey("parada_ruta.id"), nullable=False)
    producto_id = Column(Integer, ForeignKey("producto.id"), nullable=False)
    cantidad = Column(Float, nullable=False, default=0)
    peso_kg = Column(Float, nullable=False, default=0)
    volumen_m3 = Column(Float, nullable=False, default=0)

    parada_ruta = relationship("ParadaRuta", back_populates="pedidos")
    producto = relationship("Producto")
