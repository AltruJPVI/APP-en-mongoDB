from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum

class TennisLevel(str, Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"

class UserType(str, Enum):
    admin = "admin"
    company = "company"
    user = "user"

class Location(BaseModel):
    street: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    phone: Optional[str] = None

class CartItem(BaseModel):
    product_id: str
    name: str
    price: float
    quantity: int = 1
    size: Optional[str] = None

class Statistics(BaseModel):
    published_articles: int = 0
    forum_posts: int = 0

class UserCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    role: UserType = UserType.user
    password: str = Field(..., min_length=4)
    level: TennisLevel = TennisLevel.beginner  # Default beginner
    location: Optional[Location] = None  # Optional at registration
    
    @field_validator('name')
    def clean_name(cls, v):
        return v.strip()  # Remove extra spaces

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):  # Validates responses just in case
    id: str = Field(..., alias="_id")  # MongoDB uses _id, we convert it to id
    name: str
    email: EmailStr
    role: UserType
    level: TennisLevel
    location: Optional[Location] = None
    date: datetime
    statistics: Optional[Statistics] = None
    cart: Optional[List[CartItem]] = None
    
    class Config:
        populate_by_name = True  # Allows using both _id and id

class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    level: Optional[TennisLevel] = None
    location: Optional[Location] = None
    
    @field_validator('name')
    def clean_name(cls, v):
        if v:
            return v.strip()
        return v
