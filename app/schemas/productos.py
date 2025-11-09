from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from enum import Enum
from .comentarios import ComentarioReciente

# Enum para categorías
class CategoriaProducto(str, Enum):
    raquetas = "raquetas"
    zapatillas = "zapatillas"
    camisetas = "camisetas"
    pelotas = "pelotas"
    raqueteros = "raqueteros"
    gorras = "gorras"
    munequeras = "munequeras"

# Enum para género
class Genero(str, Enum):
    hombre = "hombre"
    mujer = "mujer"
    unisex = "unisex"

# Schema para stock por talla
class StockPorTalla(BaseModel):
    talla: str
    stock: int = Field(..., ge=0)  # Mayor o igual a 0

# Schema para CREAR producto
class ProductCreate(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=200)
    descripcion: str 
    precio: float = Field(..., gt=0)  # Mayor que 0
    marca: str 
    categoria: CategoriaProducto
    genero: Genero = Genero.unisex
    color: Optional[str] = None
    imagenes: Optional[List[str]] = None
    activo: bool=True
    
    # Stock: puede ser simple O por tallas
    stock: Optional[int] = Field(None, ge=0)  # Stock simple
    tallas: Optional[List[str]] = None  # Tallas disponibles (plural)
    stocks: Optional[List[StockPorTalla]] = None  # Stock por talla
    
    # Especificaciones flexibles (cualquier clave-valor)
    especificaciones: Optional[Dict[str, Any]] = None

    @field_validator('nombre', 'marca')
    def limpiar_espacios(cls, v):
        return v.strip()

    @field_validator('stocks')
    def validar_stocks(cls, v, info):
        """Si hay stocks por talla, debe haber tallas definidas"""
        if v is not None:
            tallas = info.data.get('tallas')
            if not tallas:
                raise ValueError('Si defines stocks por talla, debes proporcionar las tallas')
            # Verificar que todas las tallas en stocks existan en el array tallas
            tallas_stock = {item.talla for item in v}
            tallas_definidas = set(tallas)
            if not tallas_stock.issubset(tallas_definidas):
                raise ValueError('Todas las tallas en stocks deben estar en el array de tallas')
        return v

    @field_validator('stock')
    def validar_stock_simple(cls, v, info):
        """Si hay stock simple, no debe haber tallas ni stocks"""
        if v is not None:
            if info.data.get('tallas') or info.data.get('stocks'):
                raise ValueError('No puedes tener stock simple y stock por tallas al mismo tiempo')
        return v

# Schema de RESPUESTA (lo que devuelves al frontend)
class ProductResponse(BaseModel):
    id: str = Field(..., alias="_id")
    nombre: str
    descripcion: str
    precio: float
    marca: str
    categoria: CategoriaProducto
    genero: Genero
    color: Optional[str] = None
    imagenes: Optional[List[str]] = None
    activo:bool
    
    # Stock
    stock: Optional[int] = None
    tallas: Optional[List[str]] = None  # Corregido a plural
    stocks: Optional[List[StockPorTalla]] = None
    
    # Especificaciones
    especificaciones: Optional[Dict[str, Any]] = None
    comentarios: List[ComentarioReciente]=[]
    total_comentarios:int=0
    
    #metricas
    valoracion_promedio: Optional[float] = None  
    total_valoraciones: int = 0  
    class Config:
        populate_by_name = True

# Schema para ACTUALIZAR producto
class ProductUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=2, max_length=200)
    descripcion: Optional[str] = None
    precio: Optional[float] = Field(None, gt=0)
    marca: Optional[str] = None
    categoria: Optional[CategoriaProducto] = None
    genero: Optional[Genero] = None
    color: Optional[str] = None
    imagenes: Optional[List[str]] = None
    activo:Optional[bool]=None
    # Stock
    stock: Optional[int] = Field(None, ge=0)
    tallas: Optional[List[str]] = None  # Corregido a plural
    stocks: Optional[List[StockPorTalla]] = None
    
    # Especificaciones
    especificaciones: Optional[Dict[str, Any]] = None

    @field_validator('nombre', 'marca')
    def limpiar_espacios(cls, v):
        if v:
            return v.strip()
        return v
    
