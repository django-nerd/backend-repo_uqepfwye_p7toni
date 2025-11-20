"""
Database Schemas for the Print Studio App

Each Pydantic model represents a collection in MongoDB. The collection name
is the lowercase class name.
"""
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, EmailStr

# Core user (kept from template for reference)
class User(BaseModel):
    name: str = Field(..., description="Full name")
    email: EmailStr = Field(..., description="Email address")
    address: Optional[str] = Field(None, description="Address")
    age: Optional[int] = Field(None, ge=0, le=120, description="Age in years")
    is_active: bool = Field(True, description="Whether user is active")

# Services offered by the print studio (t-shirts, tote bags, hoodies, etc.)
class Service(BaseModel):
    key: str = Field(..., description="Machine-readable unique key, e.g., 'tshirt' or 'tote_bag'")
    name: str = Field(..., description="Public name of the service")
    description: Optional[str] = Field(None, description="Short description")
    base_price: float = Field(..., ge=0, description="Base price per unit in USD")
    categories: List[str] = Field(default_factory=list, description="Tags/categories")
    color_price_per_color: float = Field(0.2, ge=0, description="Additional price per color layer")
    print_area_multiplier: float = Field(1.0, ge=0.1, description="Multiplier for larger print areas")
    minimum_quantity: int = Field(1, ge=1, description="Minimum order quantity")

# Quote request submitted by a customer
class QuoteRequest(BaseModel):
    customer_name: str = Field(..., min_length=2)
    customer_email: EmailStr
    service_key: str = Field(..., description="Which service is requested, e.g., 'tshirt'")
    quantity: int = Field(..., ge=1, le=100000)
    colors: int = Field(1, ge=1, le=10, description="Number of print colors")
    print_area: Literal['small','medium','large'] = 'medium'
    notes: Optional[str] = None
    estimated_total: Optional[float] = Field(None, ge=0)

# Orders (optional for this MVP)
class Order(BaseModel):
    quote_id: Optional[str] = Field(None, description="Associated quote document id")
    service_key: str
    quantity: int
    total_price: float
    status: Literal['pending','confirmed','in_production','completed','cancelled'] = 'pending'
