from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uuid

# ==================== INVENTORY MODELS ====================

class StockBatch(BaseModel):
    """Stock batch for FIFO valuation"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    item_id: str
    branch_id: str
    godown_id: str
    batch_number: str
    quantity: float
    remaining_quantity: float
    unit_cost: float
    purchase_date: str
    expiry_date: Optional[str] = None
    supplier_id: Optional[str] = None
    reference_type: str  # purchase, adjustment
    reference_id: str
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class StockTransactionCreate(BaseModel):
    item_id: str
    branch_id: str
    godown_id: str
    transaction_type: str  # purchase, sale, transfer_in, transfer_out, adjustment
    quantity: float
    batch_number: Optional[str] = None
    expiry_date: Optional[str] = None
    unit_cost: Optional[float] = None
    reference_type: str
    reference_id: str
    reference_number: str
    transaction_date: str
    narration: Optional[str] = None

class StockTransaction(StockTransactionCreate):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class InterBranchTransferCreate(BaseModel):
    item_id: str
    from_branch_id: str
    to_branch_id: str
    from_godown_id: str
    to_godown_id: str
    quantity: float
    transfer_date: str
    narration: Optional[str] = None

class InterBranchTransfer(InterBranchTransferCreate):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    transfer_number: str
    status: str = "completed"
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class StockAdjustmentCreate(BaseModel):
    item_id: str
    branch_id: str
    godown_id: str
    quantity_change: float
    reason: str
    adjustment_date: str

class StockValuation(BaseModel):
    item_id: str
    branch_id: Optional[str] = None
    godown_id: Optional[str] = None
    total_quantity: float
    total_value: float
    average_cost: float
    batches: List[dict] = []
