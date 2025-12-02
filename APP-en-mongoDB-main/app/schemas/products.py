from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from enum import Enum
from .comments import LastComment

# Enum for categories
class ProductCategory(str, Enum):
    rackets = "rackets"
    shoes = "shoes"
    shirts = "shirts"
    balls = "balls"
    racket_bags = "racket_bags"
    caps = "caps"
    wristbands = "wristbands"

# Enum for gender
class Gender(str, Enum):
    male = "male"
    female = "female"
    unisex = "unisex"

# Schema for stock by size
class StockBySize(BaseModel):
    size: str
    stock: int = Field(..., ge=0)  # Greater than or equal to 0

# Schema to CREATE product
class ProductCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    price: float = Field(..., gt=0)  # Greater than 0
    brand: str 
    category: ProductCategory
    gender: Gender = Gender.unisex
    color: Optional[str] = None
    images: Optional[List[str]] = None
    active: bool = True
    
    # Stock: can be simple OR by sizes
    stock: Optional[int] = Field(None, ge=0)  # Simple stock
    sizes: Optional[List[str]] = None  # Available sizes (plural)
    stocks: Optional[List[StockBySize]] = None  # Stock by size
    
    # Flexible specifications (any key-value)
    specifications: Optional[Dict[str, Any]] = None
    
    @field_validator('name', 'brand')
    def clean_spaces(cls, v):
        return v.strip()
    
    @field_validator('stocks')
    def validate_stocks(cls, v, info):
        """If there are stocks by size, sizes must be defined"""
        if v is not None:
            sizes = info.data.get('sizes')
            if not sizes:
                raise ValueError('If you define stocks by size, you must provide the sizes')
            # Verify that all sizes in stocks exist in the sizes array
            stock_sizes = {item.size for item in v}
            defined_sizes = set(sizes)
            if not stock_sizes.issubset(defined_sizes):
                raise ValueError('All sizes in stocks must be in the sizes array')
        return v
    
    @field_validator('stock')
    def validate_simple_stock(cls, v, info):
        """If there is simple stock, there should not be sizes or stocks"""
        if v is not None:
            if info.data.get('sizes') or info.data.get('stocks'):
                raise ValueError('You cannot have simple stock and stock by sizes at the same time')
        return v

# RESPONSE Schema (what you return to the frontend)
class ProductResponse(BaseModel):
    id: str = Field(..., alias="_id")
    name: str
    price: float
    brand: str
    category: ProductCategory
    gender: Gender
    color: Optional[str] = None
    images: Optional[List[str]] = None
    active: bool
    
    # Stock
    stock: Optional[int] = None
    sizes: Optional[List[str]] = None  # Fixed to plural
    stocks: Optional[List[StockBySize]] = None
    
    # Specifications
    specifications: Optional[Dict[str, Any]] = None
    comments: List[LastComment] = []
    total_comments: int = 0
    
    # Metrics
    average_rating: Optional[float] = None  
    total_ratings: int = 0  
    
    class Config:
        populate_by_name = True

# Schema to UPDATE product
class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    price: Optional[float] = Field(None, gt=0)
    brand: Optional[str] = None
    category: Optional[ProductCategory] = None
    gender: Optional[Gender] = None
    color: Optional[str] = None
    images: Optional[List[str]] = None
    active: Optional[bool] = None
    
    # Stock
    stock: Optional[int] = Field(None, ge=0)
    sizes: Optional[List[str]] = None  # Fixed to plural
    stocks: Optional[List[StockBySize]] = None
    
    # Specifications
    specifications: Optional[Dict[str, Any]] = None
    
    @field_validator('name', 'brand')
    def clean_spaces(cls, v):
        if v:
            return v.strip()
        return v
