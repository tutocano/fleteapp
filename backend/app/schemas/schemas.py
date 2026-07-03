from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, ConfigDict


class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Empresa ----------
class EmpresaBase(BaseModel):
    nombre: str
    nit: Optional[str] = None
    direccion: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None


class EmpresaCreate(EmpresaBase):
    pass


class EmpresaOut(ORMBase, EmpresaBase):
    id: int


# ---------- Usuario / Auth (v4) ----------
# empresa_id NUNCA se acepta del cliente en la creacion/edicion de entidades de
# maestros (Centro, Cliente, Transportista, etc.) -- siempre se toma del usuario
# autenticado en el backend. Por eso los *Base/*Create de abajo ya NO incluyen
# empresa_id; solo los *Out lo exponen (para que el frontend, especialmente
# SUPER_ADMIN viendo varias empresas, sepa de cual es cada registro).
ROLES_VALIDOS = ["SUPER_ADMIN", "EMPRESA_ADMIN", "INTERFAZ", "USUARIO_FINAL"]


class UsuarioBase(BaseModel):
    nombre: str
    email: str
    rol: str
    empresa_id: Optional[int] = None
    activo: bool = True


class UsuarioCreate(UsuarioBase):
    password: str


class UsuarioUpdate(BaseModel):
    nombre: Optional[str] = None
    rol: Optional[str] = None
    empresa_id: Optional[int] = None
    activo: Optional[bool] = None
    password: Optional[str] = None  # si se envia, se cambia la contrasena


class UsuarioOut(ORMBase):
    id: int
    nombre: str
    email: str
    rol: str
    empresa_id: Optional[int] = None
    activo: bool


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioOut


# ---------- Centro Distribucion ----------
class CentroDistribucionBase(BaseModel):
    nombre: str
    codigo: Optional[str] = None
    latitud: float
    longitud: float
    direccion: Optional[str] = None


class CentroDistribucionCreate(CentroDistribucionBase):
    pass


class CentroDistribucionOut(ORMBase, CentroDistribucionBase):
    id: int
    empresa_id: int


# ---------- Tipo Cliente ----------
class TipoClienteBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = None


class TipoClienteCreate(TipoClienteBase):
    pass


class TipoClienteOut(ORMBase, TipoClienteBase):
    id: int
    empresa_id: int


# ---------- Zona Geografica ----------
class ZonaGeograficaBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    tarifa_zona: float = 0
    # Poligono aproximado [[lat, lon], ...] construido manualmente para v2
    # (ver comentario en app.models.models.ZonaGeografica). Opcional para no
    # romper zonas creadas antes de este campo.
    poligono: Optional[List[List[float]]] = None


class ZonaGeograficaCreate(ZonaGeograficaBase):
    pass


class ZonaGeograficaOut(ORMBase, ZonaGeograficaBase):
    id: int
    empresa_id: int


# ---------- Cliente ----------
class ClienteBase(BaseModel):
    tipo_cliente_id: Optional[int] = None
    zona_geografica_id: Optional[int] = None
    nombre: str
    codigo: Optional[str] = None
    latitud: float
    longitud: float
    direccion: Optional[str] = None
    canal: Optional[str] = None


class ClienteCreate(ClienteBase):
    pass


class ClienteOut(ORMBase, ClienteBase):
    id: int
    empresa_id: int


# ---------- Tipo Camion ----------
class TipoCamionBase(BaseModel):
    nombre: str
    capacidad_peso_kg: float
    capacidad_volumen_m3: float


class TipoCamionCreate(TipoCamionBase):
    pass


class TipoCamionOut(ORMBase, TipoCamionBase):
    id: int
    empresa_id: int


# ---------- Transportista ----------
class TransportistaBase(BaseModel):
    nombre: str
    nit: Optional[str] = None
    contacto: Optional[str] = None
    telefono: Optional[str] = None


class TransportistaCreate(TransportistaBase):
    pass


class TransportistaOut(ORMBase, TransportistaBase):
    id: int
    empresa_id: int
    zonas_cobertura: List["TransportistaZonaCoberturaOut"] = []


# ---------- Cobertura de zona por transportista (v3, informativa) ----------
class TransportistaZonaCoberturaOut(ORMBase):
    id: int
    transportista_id: int
    zona_geografica_id: int
    zona_geografica: Optional[ZonaGeograficaOut] = None


class ZonasCoberturaUpdate(BaseModel):
    zona_geografica_ids: List[int]


# ---------- Flota ----------
class FlotaBase(BaseModel):
    transportista_id: int
    tipo_camion_id: int
    placa: Optional[str] = None
    descripcion: Optional[str] = None
    activo: bool = True


class FlotaCreate(FlotaBase):
    pass


class FlotaOut(ORMBase, FlotaBase):
    id: int
    empresa_id: int


# ---------- Metodo Tarifa ----------
# Sin Create/Update publico: se siembra automaticamente (6 metodos fijos) al crear
# una empresa nueva (ver maestros.py). El motor de calculo identifica el metodo por
# `codigo`, no por `id`, asi que cada empresa tiene su propia fila con el mismo
# codigo pero id distinto.
class MetodoTarifaOut(ORMBase):
    id: int
    empresa_id: int
    codigo: str
    nombre: str
    descripcion: Optional[str] = None


# ---------- Tarifa Zona Detalle ----------
class TarifaZonaDetalleBase(BaseModel):
    zona_geografica_id: int
    valor: float


class TarifaZonaDetalleCreate(TarifaZonaDetalleBase):
    pass


class TarifaZonaDetalleOut(ORMBase, TarifaZonaDetalleBase):
    id: int
    tarifa_transportista_id: int


# ---------- Tarifa Transportista ----------
class TarifaTransportistaBase(BaseModel):
    transportista_id: int
    metodo_tarifa_id: int
    # None = la tarifa aplica a cualquier tipo de camion. Si se especifica, solo
    # aplica para ese tipo de camion (permite tarifas distintas por camion para
    # cualquiera de los 6 metodos).
    tipo_camion_id: Optional[int] = None
    nombre: str
    valor_unitario: float = 0
    unidad: Optional[str] = None
    activo: bool = True


class TarifaTransportistaCreate(TarifaTransportistaBase):
    zonas_detalle: Optional[List[TarifaZonaDetalleCreate]] = None


class TarifaTransportistaOut(ORMBase, TarifaTransportistaBase):
    id: int
    empresa_id: int
    zonas_detalle: List[TarifaZonaDetalleOut] = []
    tipo_camion: Optional[TipoCamionOut] = None


# ---------- Producto ----------
class ProductoBase(BaseModel):
    nombre: str
    codigo: Optional[str] = None
    peso_unitario_kg: float
    volumen_unitario_m3: float


class ProductoCreate(ProductoBase):
    pass


class ProductoOut(ORMBase, ProductoBase):
    id: int
    empresa_id: int


# ---------- Import de rutas (planificada / ejecutada) ----------
class PedidoImport(BaseModel):
    producto_id: int
    cantidad: float
    peso_kg: Optional[float] = None
    volumen_m3: Optional[float] = None


class ParadaImport(BaseModel):
    cliente_id: int
    secuencia: int
    distancia_km_tramo: Optional[float] = None
    tiempo_transito_min_tramo: Optional[float] = None
    tiempo_servicio_min: float = 0
    hora_llegada_estimada: Optional[datetime] = None
    hora_llegada_real: Optional[datetime] = None
    pedidos: List[PedidoImport] = []


class RutaImport(BaseModel):
    codigo_ruta: str
    centro_distribucion_id: int
    transportista_id: int
    tarifa_transportista_id: int
    tipo_camion_id: int
    flota_id: Optional[int] = None
    fecha: Optional[datetime] = None
    ruta_planificada_id: Optional[int] = None  # solo aplica si es ejecutada
    paradas: List[ParadaImport]


# ---------- Salida de Ruta ----------
class PedidoOut(ORMBase):
    id: int
    producto_id: int
    cantidad: float
    peso_kg: float
    volumen_m3: float


class ParadaOut(ORMBase):
    id: int
    cliente_id: int
    secuencia: int
    distancia_km_tramo: float
    tiempo_transito_min_tramo: float
    # v3: valores de referencia (Google/Haversine), independientes de lo importado.
    distancia_km_tramo_referencia: Optional[float] = None
    tiempo_transito_min_tramo_referencia: Optional[float] = None
    fuente_referencia: Optional[str] = None
    tiempo_servicio_min: float
    hora_llegada_estimada: Optional[datetime] = None
    hora_llegada_real: Optional[datetime] = None
    pedidos: List[PedidoOut] = []
    cliente: Optional[ClienteOut] = None


class RutaOut(ORMBase):
    id: int
    empresa_id: int
    codigo_ruta: str
    es_planificada: bool
    ruta_planificada_id: Optional[int] = None
    centro_distribucion_id: int
    transportista_id: int
    tarifa_transportista_id: int
    tipo_camion_id: int
    flota_id: Optional[int] = None
    fecha: datetime
    estado: str
    costo_flete_calculado: Optional[float] = None
    detalle_calculo: Optional[Dict[str, Any]] = None
    paradas: List[ParadaOut] = []
    centro_distribucion: Optional[CentroDistribucionOut] = None
    tipo_camion: Optional[TipoCamionOut] = None


class RutaListOut(ORMBase):
    id: int
    empresa_id: int
    codigo_ruta: str
    es_planificada: bool
    ruta_planificada_id: Optional[int] = None
    transportista_id: int
    fecha: datetime
    estado: str
    costo_flete_calculado: Optional[float] = None


# ---------- Conciliacion ----------
class ConciliacionRutaOut(BaseModel):
    ruta_planificada_id: int
    ruta_ejecutada_id: Optional[int]
    codigo_ruta: str
    transportista_id: int
    transportista_nombre: str
    metodo_tarifa: str
    costo_planificado: Optional[float]
    costo_real: Optional[float]
    diferencia_absoluta: Optional[float]
    diferencia_porcentual: Optional[float]


class ConciliacionTransportistaOut(BaseModel):
    transportista_id: int
    transportista_nombre: str
    total_planificado: float
    total_real: float
    diferencia_absoluta: float
    diferencia_porcentual: Optional[float]
    num_rutas: int
