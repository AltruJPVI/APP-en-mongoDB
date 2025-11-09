from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum
from .comentarios import ComentarioReciente

class TipoPost(str, Enum):
    discusion = "discusion"  
    articulo = "articulo" 

# Enum para categorías de foros
class CategoriaPost(str, Enum):
    equipamiento = "equipamiento"
    tecnica = "tecnica"
    entrenamientos = "entrenamientos"
    partidos = "partidos"
    clubes = "clubes"
    general = "general"
    consejos = "consejos"
    nutricion = "nutricion"
    noticias = "noticias"
    torneos = "torneos"

# Schema para imágenes
class Imagen(BaseModel):
    url: str
    caption: Optional[str] = None

# Schema para videos
class Video(BaseModel):
    url: str
    caption: Optional[str] = None

# Schema para CREAR discusión
class PostCreate(BaseModel):
    autor_id: str
    autor_nombre: str

    tipo: TipoPost = TipoPost.discusion 
    categoria: CategoriaPost
    titulo: str = Field(..., max_length=100)
    contenido: str = Field(..., min_length=10)  # Primer mensaje

    #opcionales
    resumen: Optional[str] = Field(None, max_length=500)
    imagenes: Optional[List[Imagen]] = None
    videos: Optional[List[Video]] = None

    @field_validator('titulo')
    def limpiar_titulo(cls, v):
        return v.strip()
    


# Schema de RESPUESTA
class PostResponse(BaseModel):
    id: str = Field(..., alias="_id")
    tipo: TipoPost
    categoria: CategoriaPost
    titulo: str
    autor_id: str
    autor_nombre: str
    fecha_creacion: datetime
    contenido: str
    resumen: Optional[str] = None
    imagenes: Optional[List[Imagen]] = None
    videos: Optional[List[Video]] = None
    
    # Métricas
    vistas: int = 0
    likes: int = 0
    
    # Comentarios/mensajes
    comentarios_: List[ComentarioReciente] = []
    total_comentarios: int = 0
    class Config:
        populate_by_name = True

# Schema para ACTUALIZAR discusión
class PostUpdate(BaseModel):

    titulo: Optional[str] = Field(None, min_length=10, max_length=200)
    contenido: Optional[str] = Field(None, min_length=10)
    resumen: Optional[str] = Field(None, max_length=500)
    categoria: Optional[CategoriaPost] = None
    imagenes: Optional[List[Imagen]] = None
    videos: Optional[List[Video]] = None
    cerrado: Optional[bool] = None

    @field_validator('titulo')
    def limpiar_titulo(cls, v):
        if v:
            return v.strip()
        return v
    


    
