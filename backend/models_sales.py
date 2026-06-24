from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uuid

# ==================== SALES MODELS ====================

class QuotationItemCreate(BaseModel):
    item_id: str
    item_name: str
    quantity: float
    rate: float
    amount: float
    description: Optional[str] = None

class QuotationCreate(BaseModel):
    customer_id: Optional[str] = None
    customer_name: str
    customer_address: str
    customer_phone: str
    branch_id: str
    quotation_date: str
    valid_until: str
    items: List[QuotationItemCreate]
    subtotal: float
    discount: float = 0
    total: float
    notes: Optional[str] = None

class Quotation(QuotationCreate):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    quotation_number: str
    status: str = "pending"  # pending, converted, expired
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class SalesOrderItemCreate(BaseModel):
    item_id: str
    item_name: str
    quantity: float
    rate: float
    amount: float

class SalesOrderCreate(BaseModel):
    customer_id: Optional[str] = None
    customer_name: str
    customer_address: str
    branch_id: str
    order_date: str
    delivery_date: Optional[str] = None
    items: List[SalesOrderItemCreate]
    subtotal: float
    discount: float = 0
    total: float
    quotation_id: Optional[str] = None

class SalesOrder(SalesOrderCreate):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    order_number: str
    status: str = "pending"  # pending, partial, completed, cancelled
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class DeliveryChallanItemCreate(BaseModel):
    item_id: str
    item_name: str
    quantity: float
    godown_id: str

class DeliveryChallanCreate(BaseModel):
    sales_order_id: str
    customer_name: str
    customer_address: str
    branch_id: str
    delivery_date: str
    items: List[DeliveryChallanItemCreate]
    vehicle_number: Optional[str] = None

class DeliveryChallan(DeliveryChallanCreate):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    challan_number: str
    status: str = "delivered"
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
