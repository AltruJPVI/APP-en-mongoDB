from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum
from .comments import LastComment

class PostType(str, Enum):
    discussion = "discussion"  
    article = "article" 

# Enum for forum categories
class PostCategory(str, Enum):
    equipment = "equipment"
    technique = "technique"
    training = "training"
    matches = "matches"
    clubs = "clubs"
    general = "general"
    tips = "tips"
    nutrition = "nutrition"
    news = "news"
    tournaments = "tournaments"

# Schema for images
class Image(BaseModel):
    url: str
    caption: Optional[str] = None

# Schema for videos
class Video(BaseModel):
    url: str
    caption: Optional[str] = None

# Schema to CREATE discussion
class PostCreate(BaseModel):
    author_id: str
    author_name: str
    type: PostType = PostType.discussion 
    category: PostCategory
    title: str = Field(..., max_length=100)
    content: str = Field(..., min_length=10)  # First message
    # Optional
    summary: Optional[str] = Field(None, max_length=500)
    images: Optional[List[Image]] = None
    videos: Optional[List[Video]] = None
    
    @field_validator('title')
    def clean_title(cls, v):
        return v.strip()
    
# RESPONSE Schema
class PostResponse(BaseModel):
    id: str = Field(..., alias="_id")
    type: PostType
    category: PostCategory
    title: str
    author_id: str
    author_name: str
    creation_date: datetime
    content: str
    summary: Optional[str] = None
    images: Optional[List[Image]] = None
    videos: Optional[List[Video]] = None
    
    # Metrics
    views: int = 0
    likes: int = 0
    
    # Comments/messages
    comments: List[LastComment] = []
    total_comments: int = 0
    
    class Config:
        populate_by_name = True

# Schema to UPDATE discussion
class PostUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=10, max_length=200)
    content: Optional[str] = Field(None, min_length=10)
    summary: Optional[str] = Field(None, max_length=500)
    category: Optional[PostCategory] = None
    images: Optional[List[Image]] = None
    videos: Optional[List[Video]] = None
    closed: Optional[bool] = None
    
    @field_validator('title')
    def clean_title(cls, v):
        if v:
            return v.strip()
        return v
