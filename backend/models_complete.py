"""
HOOREN FOOD PRODUCTS ERP - Complete Data Models
Comprehensive models for all 5 milestones
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from enum import Enum
import uuid

def get_timestamp():
    return datetime.now(timezone.utc).isoformat()

def get_uuid():
    return str(uuid.uuid4())

# ==================== ENUMS ====================

class AccountType(str, Enum):
    ASSET = "Asset"
    LIABILITY = "Liability"
    CAPITAL = "Capital"
    INCOME = "Income"
    EXPENSE = "Expense"

class BalanceType(str, Enum):
    DEBIT = "debit"
    CREDIT = "credit"

class VoucherType(str, Enum):
    JOURNAL = "journal"
    PAYMENT = "payment"
    RECEIPT = "receipt"
    CONTRA = "contra"
    DEBIT_NOTE = "debit_note"
    CREDIT_NOTE = "credit_note"
    SALES = "sales"
    PURCHASE = "purchase"

class TransactionType(str, Enum):
    PURCHASE = "purchase"
    SALE = "sale"
    TRANSFER_IN = "transfer_in"
    TRANSFER_OUT = "transfer_out"
    ADJUSTMENT = "adjustment"
    OPENING = "opening"
    RETURN_IN = "return_in"
    RETURN_OUT = "return_out"

class DocumentStatus(str, Enum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    PARTIAL = "partial"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"

class InvoiceType(str, Enum):
    GST = "gst"
    KACHA = "kacha"

class GSTSupplyType(str, Enum):
    INTRA_STATE = "intra_state"
    INTER_STATE = "inter_state"

# ==================== BRANCH ====================

class BranchCreate(BaseModel):
    code: str
    name: str
    address: str
    city: str
    state: str
    state_code: str
    pincode: str
    gstin: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    is_head_office: bool = False

class Branch(BranchCreate):
    id: str = Field(default_factory=get_uuid)
    is_active: bool = True
    created_at: str = Field(default_factory=get_timestamp)

# ==================== GODOWN ====================

class GodownCreate(BaseModel):
    code: str
    name: str
    branch_id: str
    address: Optional[str] = None
    is_default: bool = False

class Godown(GodownCreate):
    id: str = Field(default_factory=get_uuid)
    is_active: bool = True
    created_at: str = Field(default_factory=get_timestamp)

# ==================== ACCOUNT GROUP ====================

class AccountGroupCreate(BaseModel):
    code: str
    name: str
    account_type: AccountType
    parent_id: Optional[str] = None
    nature: BalanceType = BalanceType.DEBIT
    affects_gross_profit: bool = False
    description: Optional[str] = None

class AccountGroup(AccountGroupCreate):
    id: str = Field(default_factory=get_uuid)
    is_system: bool = False
    is_active: bool = True
    created_at: str = Field(default_factory=get_timestamp)

class AccountGroupTree(AccountGroup):
    children: List['AccountGroupTree'] = []
    level: int = 0

# ==================== LEDGER ====================

class LedgerCreate(BaseModel):
    name: str
    code: Optional[str] = None
    account_group_id: str
    branch_id: str
    opening_balance: float = 0.0
    balance_type: BalanceType = BalanceType.DEBIT
    gstin: Optional[str] = None
    pan: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    state_code: Optional[str] = None
    pincode: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    credit_limit: float = 0.0
    credit_days: int = 0
    is_party: bool = False

class Ledger(LedgerCreate):
    id: str = Field(default_factory=get_uuid)
    current_balance: float = 0.0
    is_active: bool = True
    created_at: str = Field(default_factory=get_timestamp)

# ==================== VOUCHER ====================

class VoucherEntryCreate(BaseModel):
    ledger_id: str
    ledger_name: str
    debit: float = 0.0
    credit: float = 0.0
    narration: Optional[str] = None
    cost_center_id: Optional[str] = None

class VoucherEntry(VoucherEntryCreate):
    id: str = Field(default_factory=get_uuid)

class VoucherCreate(BaseModel):
    voucher_type: VoucherType
    voucher_date: str
    branch_id: str
    entries: List[VoucherEntryCreate]
    narration: Optional[str] = None
    reference_number: Optional[str] = None
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    is_reversal: bool = False
    reversed_voucher_id: Optional[str] = None

class Voucher(VoucherCreate):
    id: str = Field(default_factory=get_uuid)
    voucher_number: str
    total_debit: float = 0.0
    total_credit: float = 0.0
    status: DocumentStatus = DocumentStatus.APPROVED
    created_by: str
    created_at: str = Field(default_factory=get_timestamp)
    modified_at: Optional[str] = None
    modified_by: Optional[str] = None

# ==================== LEDGER TRANSACTION ====================

class LedgerTransaction(BaseModel):
    id: str = Field(default_factory=get_uuid)
    ledger_id: str
    voucher_id: str
    voucher_number: str
    voucher_type: VoucherType
    voucher_date: str
    branch_id: str
    debit: float = 0.0
    credit: float = 0.0
    balance: float = 0.0
    narration: Optional[str] = None
    created_at: str = Field(default_factory=get_timestamp)

# ==================== ITEMS ====================

class ItemCreate(BaseModel):
    code: str
    name: str
    print_name: Optional[str] = None
    category: str
    hsn_code: str
    unit: str
    alternate_unit: Optional[str] = None
    conversion_factor: float = 1.0
    gst_rate: float
    cess_rate: float = 0.0
    cost_price: float
    selling_price: float
    mrp: Optional[float] = None
    min_stock: float = 0.0
    max_stock: float = 0.0
    reorder_level: float = 0.0
    is_batch_wise: bool = True
    is_expiry_tracking: bool = True
    description: Optional[str] = None

class Item(ItemCreate):
    id: str = Field(default_factory=get_uuid)
    is_active: bool = True
    created_at: str = Field(default_factory=get_timestamp)

# ==================== STOCK BATCH ====================

class StockBatchCreate(BaseModel):
    item_id: str
    branch_id: str
    godown_id: str
    batch_number: str
    quantity: float
    unit_cost: float
    purchase_date: str
    expiry_date: Optional[str] = None
    mfg_date: Optional[str] = None
    supplier_id: Optional[str] = None
    reference_type: str
    reference_id: str
    reference_number: str

class StockBatch(StockBatchCreate):
    id: str = Field(default_factory=get_uuid)
    remaining_quantity: float = 0.0
    is_active: bool = True
    created_at: str = Field(default_factory=get_timestamp)

# ==================== STOCK TRANSACTION ====================

class StockTransactionCreate(BaseModel):
    item_id: str
    branch_id: str
    godown_id: str
    transaction_type: TransactionType
    quantity: float
    unit_cost: float
    total_cost: float
    batch_id: Optional[str] = None
    batch_number: Optional[str] = None
    reference_type: str
    reference_id: str
    reference_number: str
    transaction_date: str
    narration: Optional[str] = None

class StockTransaction(StockTransactionCreate):
    id: str = Field(default_factory=get_uuid)
    running_qty: float = 0.0
    running_value: float = 0.0
    created_at: str = Field(default_factory=get_timestamp)

# ==================== INTER-BRANCH TRANSFER ====================

class TransferItemCreate(BaseModel):
    item_id: str
    item_name: str
    batch_id: Optional[str] = None
    batch_number: Optional[str] = None
    quantity: float
    unit_cost: float
    total_cost: float

class InterBranchTransferCreate(BaseModel):
    from_branch_id: str
    to_branch_id: str
    from_godown_id: str
    to_godown_id: str
    transfer_date: str
    items: List[TransferItemCreate]
    narration: Optional[str] = None

class InterBranchTransfer(InterBranchTransferCreate):
    id: str = Field(default_factory=get_uuid)
    transfer_number: str
    total_quantity: float = 0.0
    total_value: float = 0.0
    status: DocumentStatus = DocumentStatus.COMPLETED
    created_by: str
    created_at: str = Field(default_factory=get_timestamp)

# ==================== STOCK ADJUSTMENT ====================

class AdjustmentItemCreate(BaseModel):
    item_id: str
    item_name: str
    batch_id: Optional[str] = None
    batch_number: Optional[str] = None
    physical_qty: float
    book_qty: float
    difference: float
    unit_cost: float
    value_difference: float

class StockAdjustmentCreate(BaseModel):
    branch_id: str
    godown_id: str
    adjustment_date: str
    reason: str
    items: List[AdjustmentItemCreate]
    narration: Optional[str] = None

class StockAdjustment(StockAdjustmentCreate):
    id: str = Field(default_factory=get_uuid)
    adjustment_number: str
    total_shortage: float = 0.0
    total_excess: float = 0.0
    net_value: float = 0.0
    status: DocumentStatus = DocumentStatus.COMPLETED
    created_by: str
    created_at: str = Field(default_factory=get_timestamp)

# ==================== QUOTATION ====================

class QuotationItemCreate(BaseModel):
    item_id: str
    item_name: str
    hsn_code: str
    quantity: float
    rate: float
    discount_percent: float = 0.0
    discount_amount: float = 0.0
    taxable_amount: float
    gst_rate: float
    cgst_amount: float = 0.0
    sgst_amount: float = 0.0
    igst_amount: float = 0.0
    cess_amount: float = 0.0
    total_amount: float
    description: Optional[str] = None

class QuotationCreate(BaseModel):
    branch_id: str
    customer_id: Optional[str] = None
    customer_name: str
    customer_address: str
    customer_gstin: Optional[str] = None
    customer_state: str
    customer_state_code: str
    quotation_date: str
    valid_until: str
    items: List[QuotationItemCreate]
    subtotal: float
    discount_amount: float = 0.0
    taxable_amount: float
    cgst_amount: float = 0.0
    sgst_amount: float = 0.0
    igst_amount: float = 0.0
    cess_amount: float = 0.0
    round_off: float = 0.0
    grand_total: float
    terms: Optional[str] = None
    notes: Optional[str] = None

class Quotation(QuotationCreate):
    id: str = Field(default_factory=get_uuid)
    quotation_number: str
    status: DocumentStatus = DocumentStatus.PENDING
    created_by: str
    created_at: str = Field(default_factory=get_timestamp)

# ==================== SALES ORDER ====================

class SalesOrderItemCreate(BaseModel):
    item_id: str
    item_name: str
    hsn_code: str
    quantity: float
    delivered_qty: float = 0.0
    pending_qty: float = 0.0
    rate: float
    discount_percent: float = 0.0
    discount_amount: float = 0.0
    taxable_amount: float
    gst_rate: float
    total_amount: float

class SalesOrderCreate(BaseModel):
    branch_id: str
    customer_id: Optional[str] = None
    customer_name: str
    customer_address: str
    customer_gstin: Optional[str] = None
    customer_state: str
    customer_state_code: str
    order_date: str
    delivery_date: Optional[str] = None
    quotation_id: Optional[str] = None
    quotation_number: Optional[str] = None
    items: List[SalesOrderItemCreate]
    subtotal: float
    discount_amount: float = 0.0
    taxable_amount: float
    tax_amount: float
    round_off: float = 0.0
    grand_total: float
    notes: Optional[str] = None

class SalesOrder(SalesOrderCreate):
    id: str = Field(default_factory=get_uuid)
    order_number: str
    status: DocumentStatus = DocumentStatus.PENDING
    created_by: str
    created_at: str = Field(default_factory=get_timestamp)

# ==================== DELIVERY CHALLAN ====================

class DeliveryChallanItemCreate(BaseModel):
    item_id: str
    item_name: str
    batch_id: Optional[str] = None
    batch_number: Optional[str] = None
    godown_id: str
    quantity: float
    rate: float
    amount: float

class DeliveryChallanCreate(BaseModel):
    branch_id: str
    sales_order_id: str
    sales_order_number: str
    customer_id: Optional[str] = None
    customer_name: str
    customer_address: str
    delivery_date: str
    items: List[DeliveryChallanItemCreate]
    vehicle_number: Optional[str] = None
    driver_name: Optional[str] = None
    transport_name: Optional[str] = None
    notes: Optional[str] = None

class DeliveryChallan(DeliveryChallanCreate):
    id: str = Field(default_factory=get_uuid)
    challan_number: str
    status: DocumentStatus = DocumentStatus.COMPLETED
    created_by: str
    created_at: str = Field(default_factory=get_timestamp)

# ==================== SALES INVOICE ====================

class SalesInvoiceItemCreate(BaseModel):
    item_id: str
    item_name: str
    hsn_code: str
    batch_id: Optional[str] = None
    batch_number: Optional[str] = None
    godown_id: str
    quantity: float
    free_qty: float = 0.0
    rate: float
    discount_percent: float = 0.0
    discount_amount: float = 0.0
    taxable_amount: float
    gst_rate: float
    cgst_amount: float = 0.0
    sgst_amount: float = 0.0
    igst_amount: float = 0.0
    cess_amount: float = 0.0
    total_amount: float

class SalesInvoiceCreate(BaseModel):
    branch_id: str
    invoice_type: InvoiceType
    supply_type: GSTSupplyType
    customer_id: Optional[str] = None
    customer_name: str
    customer_address: str
    customer_gstin: Optional[str] = None
    customer_state: str
    customer_state_code: str
    invoice_date: str
    due_date: Optional[str] = None
    sales_order_id: Optional[str] = None
    delivery_challan_id: Optional[str] = None
    items: List[SalesInvoiceItemCreate]
    subtotal: float
    discount_amount: float = 0.0
    taxable_amount: float
    cgst_amount: float = 0.0
    sgst_amount: float = 0.0
    igst_amount: float = 0.0
    cess_amount: float = 0.0
    round_off: float = 0.0
    grand_total: float
    amount_in_words: str
    is_reverse_charge: bool = False
    eway_bill_number: Optional[str] = None
    notes: Optional[str] = None

class SalesInvoice(SalesInvoiceCreate):
    id: str = Field(default_factory=get_uuid)
    invoice_number: str
    voucher_id: Optional[str] = None
    status: DocumentStatus = DocumentStatus.COMPLETED
    paid_amount: float = 0.0
    balance_amount: float = 0.0
    created_by: str
    created_at: str = Field(default_factory=get_timestamp)

# ==================== SALES RETURN ====================

class SalesReturnItemCreate(BaseModel):
    item_id: str
    item_name: str
    hsn_code: str
    batch_id: Optional[str] = None
    batch_number: Optional[str] = None
    godown_id: str
    quantity: float
    rate: float
    taxable_amount: float
    gst_rate: float
    cgst_amount: float = 0.0
    sgst_amount: float = 0.0
    igst_amount: float = 0.0
    cess_amount: float = 0.0
    total_amount: float
    reason: Optional[str] = None

class SalesReturnCreate(BaseModel):
    branch_id: str
    sales_invoice_id: str
    sales_invoice_number: str
    customer_id: Optional[str] = None
    customer_name: str
    customer_gstin: Optional[str] = None
    return_date: str
    items: List[SalesReturnItemCreate]
    subtotal: float
    taxable_amount: float
    cgst_amount: float = 0.0
    sgst_amount: float = 0.0
    igst_amount: float = 0.0
    cess_amount: float = 0.0
    round_off: float = 0.0
    grand_total: float
    reason: str
    notes: Optional[str] = None

class SalesReturn(SalesReturnCreate):
    id: str = Field(default_factory=get_uuid)
    return_number: str
    voucher_id: Optional[str] = None
    status: DocumentStatus = DocumentStatus.COMPLETED
    created_by: str
    created_at: str = Field(default_factory=get_timestamp)

# ==================== PURCHASE ORDER ====================

class PurchaseOrderItemCreate(BaseModel):
    item_id: str
    item_name: str
    hsn_code: str
    quantity: float
    received_qty: float = 0.0
    pending_qty: float = 0.0
    rate: float
    discount_percent: float = 0.0
    discount_amount: float = 0.0
    taxable_amount: float
    gst_rate: float
    total_amount: float

class PurchaseOrderCreate(BaseModel):
    branch_id: str
    supplier_id: Optional[str] = None
    supplier_name: str
    supplier_address: str
    supplier_gstin: Optional[str] = None
    supplier_state: str
    supplier_state_code: str
    order_date: str
    expected_date: Optional[str] = None
    items: List[PurchaseOrderItemCreate]
    subtotal: float
    discount_amount: float = 0.0
    taxable_amount: float
    tax_amount: float
    round_off: float = 0.0
    grand_total: float
    notes: Optional[str] = None

class PurchaseOrder(PurchaseOrderCreate):
    id: str = Field(default_factory=get_uuid)
    order_number: str
    status: DocumentStatus = DocumentStatus.PENDING
    created_by: str
    created_at: str = Field(default_factory=get_timestamp)

# ==================== PURCHASE INVOICE ====================

class PurchaseInvoiceItemCreate(BaseModel):
    item_id: str
    item_name: str
    hsn_code: str
    batch_number: Optional[str] = None
    expiry_date: Optional[str] = None
    mfg_date: Optional[str] = None
    godown_id: str
    quantity: float
    free_qty: float = 0.0
    rate: float
    discount_percent: float = 0.0
    discount_amount: float = 0.0
    taxable_amount: float
    gst_rate: float
    cgst_amount: float = 0.0
    sgst_amount: float = 0.0
    igst_amount: float = 0.0
    cess_amount: float = 0.0
    total_amount: float

class PurchaseInvoiceCreate(BaseModel):
    branch_id: str
    supply_type: GSTSupplyType
    supplier_id: Optional[str] = None
    supplier_name: str
    supplier_address: str
    supplier_gstin: Optional[str] = None
    supplier_state: str
    supplier_state_code: str
    supplier_invoice_number: str
    supplier_invoice_date: str
    invoice_date: str
    purchase_order_id: Optional[str] = None
    items: List[PurchaseInvoiceItemCreate]
    subtotal: float
    discount_amount: float = 0.0
    taxable_amount: float
    cgst_amount: float = 0.0
    sgst_amount: float = 0.0
    igst_amount: float = 0.0
    cess_amount: float = 0.0
    round_off: float = 0.0
    grand_total: float
    is_reverse_charge: bool = False
    tds_rate: float = 0.0
    tds_amount: float = 0.0
    net_payable: float = 0.0
    notes: Optional[str] = None

class PurchaseInvoice(PurchaseInvoiceCreate):
    id: str = Field(default_factory=get_uuid)
    invoice_number: str
    voucher_id: Optional[str] = None
    status: DocumentStatus = DocumentStatus.COMPLETED
    paid_amount: float = 0.0
    balance_amount: float = 0.0
    created_by: str
    created_at: str = Field(default_factory=get_timestamp)

# ==================== PURCHASE RETURN ====================

class PurchaseReturnItemCreate(BaseModel):
    item_id: str
    item_name: str
    hsn_code: str
    batch_id: Optional[str] = None
    batch_number: Optional[str] = None
    godown_id: str
    quantity: float
    rate: float
    taxable_amount: float
    gst_rate: float
    cgst_amount: float = 0.0
    sgst_amount: float = 0.0
    igst_amount: float = 0.0
    cess_amount: float = 0.0
    total_amount: float
    reason: Optional[str] = None

class PurchaseReturnCreate(BaseModel):
    branch_id: str
    purchase_invoice_id: str
    purchase_invoice_number: str
    supplier_id: Optional[str] = None
    supplier_name: str
    supplier_gstin: Optional[str] = None
    return_date: str
    items: List[PurchaseReturnItemCreate]
    subtotal: float
    taxable_amount: float
    cgst_amount: float = 0.0
    sgst_amount: float = 0.0
    igst_amount: float = 0.0
    cess_amount: float = 0.0
    round_off: float = 0.0
    grand_total: float
    reason: str
    notes: Optional[str] = None

class PurchaseReturn(PurchaseReturnCreate):
    id: str = Field(default_factory=get_uuid)
    return_number: str
    voucher_id: Optional[str] = None
    status: DocumentStatus = DocumentStatus.COMPLETED
    created_by: str
    created_at: str = Field(default_factory=get_timestamp)

# ==================== GST MODELS ====================

class HSNMasterCreate(BaseModel):
    hsn_code: str
    description: str
    gst_rate: float
    cess_rate: float = 0.0

class HSNMaster(HSNMasterCreate):
    id: str = Field(default_factory=get_uuid)
    is_active: bool = True
    created_at: str = Field(default_factory=get_timestamp)

class GSTLedgerMapping(BaseModel):
    id: str = Field(default_factory=get_uuid)
    tax_type: str  # cgst, sgst, igst, cess
    input_ledger_id: str
    output_ledger_id: str
    is_active: bool = True

# ==================== REPORT MODELS ====================

class TrialBalanceItem(BaseModel):
    ledger_id: str
    ledger_name: str
    group_name: str
    account_type: str
    opening_debit: float = 0.0
    opening_credit: float = 0.0
    debit: float = 0.0
    credit: float = 0.0
    closing_debit: float = 0.0
    closing_credit: float = 0.0

class TrialBalanceReport(BaseModel):
    as_on_date: str
    branch_id: Optional[str] = None
    branch_name: Optional[str] = None
    items: List[TrialBalanceItem]
    total_opening_debit: float = 0.0
    total_opening_credit: float = 0.0
    total_debit: float = 0.0
    total_credit: float = 0.0
    total_closing_debit: float = 0.0
    total_closing_credit: float = 0.0
    is_balanced: bool = True
    difference: float = 0.0

class ProfitLossItem(BaseModel):
    group_name: str
    ledgers: List[Dict[str, Any]]
    total: float = 0.0

class ProfitLossReport(BaseModel):
    period_start: str
    period_end: str
    branch_id: Optional[str] = None
    trading_account: Dict[str, Any]
    income_items: List[ProfitLossItem]
    expense_items: List[ProfitLossItem]
    gross_profit: float = 0.0
    net_profit: float = 0.0
    total_income: float = 0.0
    total_expense: float = 0.0

class BalanceSheetItem(BaseModel):
    group_name: str
    ledgers: List[Dict[str, Any]]
    total: float = 0.0

class BalanceSheetReport(BaseModel):
    as_on_date: str
    branch_id: Optional[str] = None
    asset_items: List[BalanceSheetItem]
    liability_items: List[BalanceSheetItem]
    capital_items: List[BalanceSheetItem]
    total_assets: float = 0.0
    total_liabilities: float = 0.0
    total_capital: float = 0.0
    net_profit: float = 0.0
    is_balanced: bool = True

class StockLedgerItem(BaseModel):
    date: str
    voucher_number: str
    voucher_type: str
    party_name: Optional[str] = None
    batch_number: Optional[str] = None
    in_qty: float = 0.0
    out_qty: float = 0.0
    rate: float = 0.0
    value: float = 0.0
    balance_qty: float = 0.0
    balance_value: float = 0.0

class StockLedgerReport(BaseModel):
    item_id: str
    item_name: str
    branch_id: Optional[str] = None
    godown_id: Optional[str] = None
    period_start: str
    period_end: str
    opening_qty: float = 0.0
    opening_value: float = 0.0
    transactions: List[StockLedgerItem]
    closing_qty: float = 0.0
    closing_value: float = 0.0
    average_cost: float = 0.0

# ==================== GST REPORT MODELS ====================

class GSTR1B2BItem(BaseModel):
    rt: float  # Rate
    txval: float  # Taxable value
    camt: float = 0.0  # CGST
    samt: float = 0.0  # SGST
    iamt: float = 0.0  # IGST
    csamt: float = 0.0  # CESS

class GSTR1B2BInvoice(BaseModel):
    inum: str  # Invoice number
    idt: str  # Invoice date DD-MM-YYYY
    val: float  # Total value
    pos: str  # Place of supply state code
    rchrg: str = "N"  # Reverse charge
    inv_typ: str = "R"  # R=Regular, SEZWP, SEZWOP, DE, CBW
    itms: List[Dict[str, Any]]

class GSTR1B2B(BaseModel):
    ctin: str  # Customer GSTIN
    inv: List[GSTR1B2BInvoice]

class GSTR1B2CS(BaseModel):
    sply_ty: str = "INTRA"  # INTER/INTRA
    pos: str  # Place of supply
    typ: str = "OE"  # OE=outward supply
    rt: float  # Rate
    txval: float  # Taxable value
    camt: float = 0.0
    samt: float = 0.0
    iamt: float = 0.0
    csamt: float = 0.0

class GSTR1HSNItem(BaseModel):
    num: int  # S.No
    hsn_sc: str  # HSN/SAC code
    desc: str  # Description
    uqc: str  # Unit
    qty: float
    val: float  # Total value
    txval: float  # Taxable value
    camt: float = 0.0
    samt: float = 0.0
    iamt: float = 0.0
    csamt: float = 0.0

class GSTR1Report(BaseModel):
    gstin: str
    fp: str  # Filing period MMYYYY
    b2b: List[GSTR1B2B]
    b2cs: List[GSTR1B2CS]
    b2cl: List[Dict[str, Any]]  # B2C Large (>2.5L inter-state)
    cdnr: List[Dict[str, Any]]  # Credit/Debit notes registered
    cdnur: List[Dict[str, Any]]  # Credit/Debit notes unregistered
    exp: List[Dict[str, Any]]  # Exports
    hsn: Dict[str, Any]  # HSN summary

class GSTR3BSupplySummary(BaseModel):
    txval: float = 0.0
    iamt: float = 0.0
    camt: float = 0.0
    samt: float = 0.0
    csamt: float = 0.0

class GSTR3BReport(BaseModel):
    gstin: str
    ret_period: str  # MMYYYY
    outward_taxable_supplies: GSTR3BSupplySummary
    outward_zero_rated: GSTR3BSupplySummary
    outward_nil_rated: GSTR3BSupplySummary
    outward_exempt: GSTR3BSupplySummary
    inward_reverse_charge: GSTR3BSupplySummary
    inward_isd: GSTR3BSupplySummary
    eligible_itc: Dict[str, float]
    ineligible_itc: Dict[str, float]
    net_tax_liability: Dict[str, float]
    interest: float = 0.0
    late_fee: float = 0.0
