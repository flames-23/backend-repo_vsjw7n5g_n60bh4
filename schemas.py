from typing import List, Optional
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime

# Users
class User(BaseModel):
    email: EmailStr
    name: str = Field(..., description="Full name")
    role: str = Field("customer", description="customer | admin")
    is_active: bool = True

# Products
class Product(BaseModel):
    name: str
    description: Optional[str] = None
    price: float = Field(..., ge=0)
    image: Optional[str] = None
    stock: int = Field(0, ge=0)
    category: Optional[str] = None

# Orders
class OrderItem(BaseModel):
    product_id: str
    quantity: int = Field(..., ge=1)

class Order(BaseModel):
    user_email: EmailStr
    items: List[OrderItem]
    status: str = Field("queued", description="queued|processing|ready|failed")
    progress: int = Field(0, ge=0, le=100)
    total_items: int = 0

# Dispense logs
class DispenseLog(BaseModel):
    order_id: str
    product_id: str
    quantity: int
    status: str = Field("dispensed", description="dispensed|failed")
    note: Optional[str] = None

# Shelf mapping
class ShelfCell(BaseModel):
    cell_code: str = Field(..., description="e.g., A1..A20")
    product_id: Optional[str] = None
    stock: int = Field(0, ge=0)
    motor_active: bool = False
    sensor_value: Optional[float] = None

# Note: The Flames database viewer will automatically read these schemas on /schema
