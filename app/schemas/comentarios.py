from pydantic import BaseModel, Field, field_validator
from typing import Optional,List
from datetime import datetime
from enum import Enum


#caché de los últimos comentarios
class ComentarioReciente(BaseModel):
    id: str = Field(..., alias="_id")
    usuario_id: str
    usuario_nombre: str
    texto: str
    fecha: datetime
    likes: int = 0
    archivo_adicional:Optional[List[str]] = None
    valoracion: Optional[int] = Field(None, ge=1, le=5) #estrellas

    class Config:
        populate_by_name = True

        
class TipoEntidad(str, Enum):
    producto = "producto"
    post = "post"

class CommentCreate(BaseModel):

    entidad_tipo: TipoEntidad 
    entidad_id: str  
    usuario_id: str
    usuario_nombre: str  
    texto: str = Field(..., min_length=1, max_length=1000)
    archivo_adicional:Optional[List[str]] = None
    respuesta_a: Optional[str] = None  # ID del comentario padre, null si es principal
    valoracion: Optional[int] = Field(None, ge=1, le=5) 
    

    @field_validator('texto')
    def limpiar_texto(cls, v):
        return v.strip()

# Schema de RESPUESTA del comentario
class CommentResponse(BaseModel):
    id: str = Field(..., alias="_id")
    entidad_tipo: TipoEntidad
    entidad_id: str
    usuario_id: str
    usuario_nombre: str
    texto: str
    archivo_adicional:Optional[List[str]] = None
    fecha: datetime
    likes: int = 0
    respuesta_a: Optional[str] = None
    valoracion: Optional[int] = Field(None, ge=1, le=5) 
    
    class Config:
        populate_by_name = True

# Schema para ACTUALIZAR comentario
class CommentUpdate(BaseModel):
    texto: Optional[str] = Field(None, min_length=1, max_length=1000)
    archivo_adicional:Optional[List[str]] = None
    valoracion: Optional[int] = Field(None, ge=1, le=5) 
    
    @field_validator('texto')
    def limpiar_texto(cls, v):
        if v:
            return v.strip()
        return v
