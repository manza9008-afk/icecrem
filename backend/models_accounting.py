from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uuid

# ==================== CHART OF ACCOUNTS ====================

class AccountGroupCreate(BaseModel):
    code: str
    name: str
    account_type: str  # Asset, Liability, Capital, Income, Expense
    parent_id: Optional[str] = None
    description: Optional[str] = None

class AccountGroup(AccountGroupCreate):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    is_active: bool = True
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class AccountGroupTree(AccountGroup):
    children: List['AccountGroupTree'] = []

# ==================== LEDGERS ====================

class LedgerCreate(BaseModel):
    name: str
    account_group_id: str
    opening_balance: float = 0.0
    balance_type: str = "debit"  # debit or credit
    branch_id: Optional[str] = None
    is_active: bool = True

class Ledger(LedgerCreate):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    current_balance: float = 0.0
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

# ==================== VOUCHERS ====================

class VoucherEntryItem(BaseModel):
    ledger_id: str
    ledger_name: str
    entry_type: str  # debit or credit
    amount: float
    narration: Optional[str] = None

class VoucherCreate(BaseModel):
    voucher_type: str  # journal, payment, receipt, contra, debit_note, credit_note
    voucher_date: str
    entries: List[VoucherEntryItem]
    narration: Optional[str] = None
    reference_number: Optional[str] = None
    branch_id: Optional[str] = None

class Voucher(VoucherCreate):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    voucher_number: str
    total_amount: float
    is_approved: bool = False
    created_by: str
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    modified_at: Optional[str] = None

# ==================== BRANCHES ====================

class BranchCreate(BaseModel):
    code: str
    name: str
    address: str
    gstin: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    is_head_office: bool = False

class Branch(BranchCreate):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    is_active: bool = True
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

# ==================== GODOWNS ====================

class GodownCreate(BaseModel):
    code: str
    name: str
    branch_id: str
    address: Optional[str] = None
    is_active: bool = True

class Godown(GodownCreate):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
