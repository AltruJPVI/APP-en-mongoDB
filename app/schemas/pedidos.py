from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum
from .usuarios import Ubicacion

# Enum para método de pago
class MetodoPago(str, Enum):
    tarjeta = "tarjeta"
    paypal = "paypal"
    transferencia = "transferencia"

# Schema para item del pedido
class ItemPedido(BaseModel):
    id_producto: str
    nombre: str  # Guardamos nombre histórico
    precio: float = Field(..., gt=0)  # Precio al momento de compra
    cantidad: int = Field(..., gt=0)
    talla: Optional[str] = None
    imagen: Optional[str] = None

# Schema para CREAR pedido
class OrderCreate(BaseModel):
    user_id: str  # ID del usuario que compra
    items: List[ItemPedido] = Field(..., min_length=1)  # Al menos 1 item
    total: float = Field(..., gt=0)
    direccion_envio: Ubicacion  # Reutilizamos del usuario
    metodo_pago: MetodoPago

class OrderResponse(BaseModel):
    id: str = Field(..., alias="_id")
    numero_pedido: str  # Generado automáticamente (ej: PED-2025-001)
    user_id: str
    fecha_pedido: datetime
    items: List[ItemPedido]
    total: float
    direccion_envio: Ubicacion
    metodo_pago: MetodoPago

    class Config:
        populate_by_name = True

