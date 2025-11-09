from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum

class NivelTenis(str, Enum):
    principiante = "principiante"
    intermedio = "intermedio"
    avanzado = "avanzado"

class TipoUsuario(str,Enum):
    admin="admin"
    empresa="empresa"
    user="user"

class Ubicacion(BaseModel):
    calle: Optional[str] = None
    ciudad: Optional[str] = None
    codigo_postal: Optional[str] = None
    telefono: Optional[str] = None

class ItemCarrito(BaseModel):
    id_producto: str
    nombre: str
    precio: float
    cantidad: int = 1
    talla: Optional[str]=None

class Estadisticas(BaseModel):
    articulos_publicados: int = 0
    eventos_creados: int = 0
    posts_en_foros: int = 0

class UserCreate(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    clase: TipoUsuario=TipoUsuario.user
    password: str = Field(..., min_length=4)
    nivel: NivelTenis = NivelTenis.principiante  # Por defecto principiante
    ubicacion: Optional[Ubicacion] = None  # Opcional al registrarse

    @field_validator('nombre')
    def validar_nombre(cls, v):
        return v.strip()  # Elimina espacios extra 

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):#valida las respuestas por si acaso
    id: str = Field(..., alias="_id")  # MongoDB usa _id, lo convertimos a id
    nombre: str
    email: EmailStr
    clase:TipoUsuario
    nivel: NivelTenis
    ubicacion: Optional[Ubicacion] = None
    fecha_registro: datetime
    estadisticas: Optional[Estadisticas] = None
    carrito: Optional[List[ItemCarrito]] = None

    class Config:
        populate_by_name = True  # Permite usar tanto _id como id

class UserUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=2, max_length=100)
    nivel: Optional[NivelTenis] = None
    ubicacion: Optional[Ubicacion] = None

    @field_validator('nombre')
    def validar_nombre(cls, v):
        if v:
            return v.strip()
        return v
    
