from pydantic import BaseModel, Field, field_validator
from typing import Optional,List
from datetime import datetime
from enum import Enum


#caché de los últimos comentarios
class LastComment(BaseModel):
    id: str = Field(..., alias="_id")
    user_id: str
    user_name: str
    text: str
    date: datetime
    likes: int = 0
    additional_file:Optional[List[str]] = None
    rating: Optional[int] = Field(None, ge=1, le=5) #stars

    class Config:
        populate_by_name = True

        
class EntityType(str, Enum):
    product = "product"
    post = "post"

class CommentCreate(BaseModel):

    entity_type: EntityType 
    entity_id: str  
    user_id: str
    user_name: str  
    text: str = Field(..., min_length=1, max_length=1000)
    additional_file:Optional[List[str]] = None
    response_to: Optional[str] = None  
    rating: Optional[int] = Field(None, ge=1, le=5) 
    

    @field_validator('text')
    def clean_text(cls, v):
        return v.strip()

class CommentResponse(BaseModel):
    id: str = Field(..., alias="_id")
    entity_type: EntityType
    entity_id: str
    usuer_id: str
    user_name: str
    text: str
    additional_file:Optional[List[str]] = None
    date: datetime
    likes: int = 0
    response_to: Optional[str] = None
    rating: Optional[int] = Field(None, ge=1, le=5) 
    
    class Config:
        populate_by_name = True

# Schema para ACTUALIZAR comentario
class CommentUpdate(BaseModel):
    text: Optional[str] = Field(None, min_length=1, max_length=1000)
    additional_file:Optional[List[str]] = None
    rating: Optional[int] = Field(None, ge=1, le=5) 
    
    @field_validator('text')
    def clean_text(cls, v):
        if v:
            return v.strip()
        return v
