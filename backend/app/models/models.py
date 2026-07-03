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


# v4: roles fijos del sistema. Un usuario tiene exactamente UNO de estos roles.
# SUPER_ADMIN no pertenece a ninguna empresa (empresa_id NULL); los otros 3 roles
# pertenecen exactamente a una empresa (empresa_id obligatorio).
ROLES_VALIDOS = ["SUPER_ADMIN", "EMPRESA_ADMIN", "INTERFAZ", "USUARIO_FINAL"]


class Usuario(Base):
    __tablename__ = "usuario"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(200), nullable=False)
    email = Column(String(200), nullable=False, unique=True, index=True)
    password_hash = Column(String(200), nullable=False)
    # Ver ROLES_VALIDOS. Se guarda como string simple (no enum nativo de Postgres)
    # para no complicar migraciones futuras si se agregan roles.
    rol = Column(String(30), nullable=False)
    # NULL solo para SUPER_ADMIN. Para los otros 3 roles es obligatorio (validado en
    # el schema/endpoint, no a nivel de columna, para poder dar un mensaje claro).
    empresa_id = Column(Integer, ForeignKey("empresa.id"), nullable=True)
    activo = Column(Boolean, nullable=False, default=True)
    creado_en = Column(DateTime, default=datetime.utcnow)

    empresa = relationship("Empresa")


class CentroDistribucion(Base):
    __tablename__ = "centro_distribucion"
    __table_args__ = (
        UniqueConstraint("empresa_id", "codigo", name="uq_centro_distribucion_empresa_codigo"),
    )

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresa.id"), nullable=False)
    nombre = Column(String(200), nullable=False)
    codigo = Column(String(50))
    latitud = Column(Float, nullable=False)
    longitud = Column(Float, nullable=False)
    direccion = Column(String(300))
    creado_en = Column(DateTime, default=datetime.utcnow)

    empresa = relationship("Empresa", back_populates="centros")


class TipoCliente(Base):
    __tablename__ = "tipo_cliente"
    __table_args__ = (
        UniqueConstraint("empresa_id", "nombre", name="uq_tipo_cliente_empresa_nombre"),
    )

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresa.id"), nullable=False)
    nombre = Column(String(100), nullable=False)
    descripcion = Column(String(300))

    empresa = relationship("Empresa")


class ZonaGeografica(Base):
    __tablename__ = "zona_geografica"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresa.id"), nullable=False)
    nombre = Column(String(150), nullable=False)
    descripcion = Column(String(300))
    tarifa_zona = Column(Float, nullable=False, default=0)
    # Poligono aproximado (lista de [lat, lon]) que delimita la zona en el mapa.
    # v2: construido manualmente a partir del conocimiento general de las localidades
    # de Bogota (8-15 vertices, sin auto-interseccion), NO es un shapefile oficial.
    # Se guarda como JSON para no acoplar el modelo a una libreria geoespacial
    # especifica; en el futuro puede reemplazarse por un poligono importado desde
    # el GeoJSON oficial de localidades de IDECA (https://www.ideca.gov.co/) sin
    # cambiar el esquema: basta con sobreescribir este campo con las coordenadas
    # reales (siempre como lista de pares [lat, lon]).
    poligono = Column(JSON, nullable=True)
    creado_en = Column(DateTime, default=datetime.utcnow)

    empresa = relationship("Empresa")


class Cliente(Base):
    __tablename__ = "cliente"
    __table_args__ = (
        UniqueConstraint("empresa_id", "codigo", name="uq_cliente_empresa_codigo"),
    )

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresa.id"), nullable=False)
    tipo_cliente_id = Column(Integer, ForeignKey("tipo_cliente.id"))
    zona_geografica_id = Column(Integer, ForeignKey("zona_geografica.id"))
    nombre = Column(String(200), nullable=False)
    codigo = Column(String(50))
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
    empresa_id = Column(Integer, ForeignKey("empresa.id"), nullable=False)
    nombre = Column(String(100), nullable=False)
    capacidad_peso_kg = Column(Float, nullable=False)
    capacidad_volumen_m3 = Column(Float, nullable=False)

    empresa = relationship("Empresa")


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
    zonas_cobertura = relationship(
        "TransportistaZonaCobertura", back_populates="transportista", cascade="all, delete-orphan"
    )


class TransportistaZonaCobertura(Base):
    """v3: relacion muchos-a-muchos entre transportista y zona geografica que indica
    que zonas atiende cada transportista. Es puramente informativa/de consulta (no
    bloquea la importacion de rutas) -- decision explicita del usuario para v3."""

    __tablename__ = "transportista_zona_cobertura"
    __table_args__ = (
        UniqueConstraint(
            "transportista_id", "zona_geografica_id", name="uq_transportista_zona_cobertura"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    transportista_id = Column(Integer, ForeignKey("transportista.id"), nullable=False)
    zona_geografica_id = Column(Integer, ForeignKey("zona_geografica.id"), nullable=False)

    transportista = relationship("Transportista", back_populates="zonas_cobertura")
    zona_geografica = relationship("ZonaGeografica")


class Flota(Base):
    __tablename__ = "flota"

    id = Column(Integer, primary_key=True, index=True)
    # v4: agregado por consistencia del filtro por empresa (ya era derivable via
    # transportista_id -> transportista.empresa_id). Debe coincidir siempre con la
    # empresa del transportista; se valida al crear/actualizar.
    empresa_id = Column(Integer, ForeignKey("empresa.id"), nullable=False)
    transportista_id = Column(Integer, ForeignKey("transportista.id"), nullable=False)
    tipo_camion_id = Column(Integer, ForeignKey("tipo_camion.id"), nullable=False)
    placa = Column(String(20))
    descripcion = Column(String(200))
    activo = Column(Boolean, default=True)

    empresa = relationship("Empresa")
    transportista = relationship("Transportista", back_populates="flota")
    tipo_camion = relationship("TipoCamion")


class MetodoTarifa(Base):
    __tablename__ = "metodo_tarifa"
    __table_args__ = (
        UniqueConstraint("empresa_id", "codigo", name="uq_metodo_tarifa_empresa_codigo"),
    )

    id = Column(Integer, primary_key=True, index=True)
    # v4: por empresa (cada empresa nueva recibe una copia de los 6 metodos al
    # crearse -- ver maestros.py). El motor de calculo (flete_calculo.py) sigue
    # identificando el metodo por su `codigo`, no por `id`, asi que no cambia.
    empresa_id = Column(Integer, ForeignKey("empresa.id"), nullable=False)
    codigo = Column(String(50), nullable=False)
    nombre = Column(String(150), nullable=False)
    descripcion = Column(String(400))

    empresa = relationship("Empresa")


class TarifaTransportista(Base):
    __tablename__ = "tarifa_transportista"

    id = Column(Integer, primary_key=True, index=True)
    # v4: agregado por consistencia del filtro por empresa (ya era derivable via
    # transportista_id). Debe coincidir siempre con la empresa del transportista.
    empresa_id = Column(Integer, ForeignKey("empresa.id"), nullable=False)
    transportista_id = Column(Integer, ForeignKey("transportista.id"), nullable=False)
    metodo_tarifa_id = Column(Integer, ForeignKey("metodo_tarifa.id"), nullable=False)
    # Si es NULL, la tarifa aplica a cualquier tipo de camion (comportamiento v1,
    # retrocompatible). Si se especifica, esta tarifa SOLO aplica para ese tipo de
    # camion puntual -- asi un mismo transportista/metodo puede tener valores
    # distintos segun el camion usado (ej. POR_VIAJE con NHR vs con Sencillo).
    # Esta unica columna generaliza la variable "tipo de camion" a los 6 metodos
    # de tarifa sin tocar la logica de calculo de cada uno: el calculo siempre usa
    # el valor_unitario/zonas_detalle de la fila de tarifa ya seleccionada.
    tipo_camion_id = Column(Integer, ForeignKey("tipo_camion.id"), nullable=True)
    nombre = Column(String(150), nullable=False)
    valor_unitario = Column(Float, nullable=False, default=0)
    unidad = Column(String(30))
    activo = Column(Boolean, default=True)
    creado_en = Column(DateTime, default=datetime.utcnow)

    empresa = relationship("Empresa")
    transportista = relationship("Transportista", back_populates="tarifas")
    metodo_tarifa = relationship("MetodoTarifa")
    tipo_camion = relationship("TipoCamion")
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
    __table_args__ = (
        UniqueConstraint("empresa_id", "codigo", name="uq_producto_empresa_codigo"),
    )

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresa.id"), nullable=False)
    nombre = Column(String(200), nullable=False)
    codigo = Column(String(50))
    peso_unitario_kg = Column(Float, nullable=False)
    volumen_unitario_m3 = Column(Float, nullable=False)

    empresa = relationship("Empresa")


class Ruta(Base):
    __tablename__ = "ruta"

    id = Column(Integer, primary_key=True, index=True)
    # v4: agregado por consistencia del filtro por empresa (ya era derivable via
    # centro_distribucion_id -> centro_distribucion.empresa_id). Se fija al crear la
    # ruta a partir del CEDI, y se valida que transportista/tarifa/tipo_camion sean
    # de la misma empresa.
    empresa_id = Column(Integer, ForeignKey("empresa.id"), nullable=False)
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

    empresa = relationship("Empresa")
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
    # v3: distancia/tiempo de REFERENCIA obtenidos siempre del conector de distancia
    # (Google Routes API o Haversine, ver distance_connector.py), independientemente
    # de si distancia_km_tramo/tiempo_transito_min_tramo vinieron dados en el JSON de
    # importacion. Sirven para comparar "lo importado" vs "lo que dice un calculo
    # objetivo" y asi detectar si una ruta se planifico o ejecuto con datos incorrectos.
    # No pisan nunca los valores importados.
    distancia_km_tramo_referencia = Column(Float, nullable=True)
    tiempo_transito_min_tramo_referencia = Column(Float, nullable=True)
    fuente_referencia = Column(String(30), nullable=True)  # GOOGLE_ROUTES_API | HAVERSINE_FALLBACK
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
