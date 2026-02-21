from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from datetime import datetime
import uuid

class LoginRequest(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    username: str
    email: str
    full_name: str
    require_password_change: bool = False

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str

class DashboardStats(BaseModel):
    today_sales: float
    monthly_sales: float
    low_stock_items: int
    outstanding_receivables: float

class ItemCreate(BaseModel):
    name: str
    sku: str
    category: str
    hsn: str = "2105"
    gst_rate: float
    unit: str
    cost_price: float
    selling_price: float
    reorder_level: int = 10
    opening_stock: float = 0

class Item(ItemCreate):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class CustomerCreate(BaseModel):
    name: str
    address: str
    gstin: Optional[str] = None
    pan: Optional[str] = None
    phone: str
    email: Optional[str] = None
    credit_limit: float = 0

class Customer(CustomerCreate):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class SupplierCreate(BaseModel):
    name: str
    address: str
    gstin: Optional[str] = None
    pan: Optional[str] = None
    phone: str
    email: Optional[str] = None

class Supplier(SupplierCreate):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class InvoiceItem(BaseModel):
    item_id: str
    item_name: str
    hsn: str
    quantity: float
    rate: float
    amount: float
    gst_rate: float
    batch_no: Optional[str] = None
    expiry_date: Optional[str] = None

class SalesInvoiceCreate(BaseModel):
    invoice_type: str  # "gst" or "kacha"
    customer_name: str
    customer_gstin: Optional[str] = None
    customer_address: str
    invoice_date: str
    items: List[InvoiceItem]
    discount: Optional[float] = 0
    notes: Optional[str] = None

class SalesInvoice(SalesInvoiceCreate):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    invoice_number: str
    subtotal: float
    tax_amount: float
    grand_total: float
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class PurchaseInvoiceCreate(BaseModel):
    supplier_name: str
    supplier_gstin: Optional[str] = None
    invoice_date: str
    items: List[InvoiceItem]

class PurchaseInvoice(PurchaseInvoiceCreate):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    invoice_number: str
    subtotal: float
    tax_amount: float
    grand_total: float
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
