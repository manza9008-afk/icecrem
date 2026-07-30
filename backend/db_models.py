from sqlalchemy import Boolean, Column, DateTime, Float, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import declarative_base


Base = declarative_base()


class TimestampMixin:
    created_at = Column(DateTime(timezone=True), nullable=True)
    modified_at = Column(DateTime(timezone=True), nullable=True)


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    username = Column(String(80), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    full_name = Column(String(255), nullable=False)
    require_password_change = Column(Boolean, default=True)
    last_login = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)


class CompanySettings(Base):
    __tablename__ = "company_settings"

    id = Column(String, primary_key=True)
    business_name = Column(String(255), nullable=True)
    trade_name = Column(String(255), nullable=True)
    legal_name = Column(String(255), nullable=True)
    name = Column(String(255), nullable=True)
    gstin = Column(String(20), nullable=True)
    pan = Column(String(20), nullable=True)
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    state_code = Column(String(10), nullable=True)
    pincode = Column(String(20), nullable=True)
    pin_code = Column(String(20), nullable=True)
    country = Column(String(100), nullable=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    website = Column(String(255), nullable=True)
    cin = Column(String(50), nullable=True)
    tan = Column(String(50), nullable=True)
    bank_name = Column(String(255), nullable=True)
    account_number = Column(String(100), nullable=True)
    bank_account = Column(String(100), nullable=True)
    ifsc = Column(String(50), nullable=True)
    bank_ifsc = Column(String(50), nullable=True)
    branch = Column(String(255), nullable=True)
    bank_branch = Column(String(255), nullable=True)
    upi_id = Column(String(100), nullable=True)
    logo_url = Column(String(255), nullable=True)
    signature_url = Column(String(255), nullable=True)
    invoice_prefix = Column(String(50), nullable=True)
    invoice_terms = Column(Text, nullable=True)
    default_credit_days = Column(Integer, default=30)
    financial_year_start_month = Column(Integer, default=4)
    financial_year = Column(String(20), nullable=True)
    currency = Column(String(20), default="INR")
    currency_symbol = Column(String(10), default="Rs")
    decimal_places = Column(Integer, default=2)


class Branch(Base, TimestampMixin):
    __tablename__ = "branches"

    id = Column(String, primary_key=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    state_code = Column(String(10), nullable=True)
    pincode = Column(String(20), nullable=True)
    gstin = Column(String(20), nullable=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    is_head_office = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)


class Godown(Base, TimestampMixin):
    __tablename__ = "godowns"

    id = Column(String, primary_key=True)
    code = Column(String(50), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    branch_id = Column(String, nullable=False, index=True)
    address = Column(Text, nullable=True)
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)


class AccountGroup(Base, TimestampMixin):
    __tablename__ = "account_groups"

    id = Column(String, primary_key=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    account_type = Column(String(50), nullable=False)
    parent_id = Column(String, nullable=True, index=True)
    nature = Column(String(20), default="debit")
    affects_gross_profit = Column(Boolean, default=False)
    description = Column(Text, nullable=True)
    is_system = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)


class Ledger(Base, TimestampMixin):
    __tablename__ = "ledgers"

    id = Column(String, primary_key=True)
    name = Column(String(255), nullable=False, index=True)
    code = Column(String(100), nullable=True, index=True)
    account_group_id = Column(String, nullable=False, index=True)
    branch_id = Column(String, nullable=True, index=True)
    opening_balance = Column(Float, default=0.0)
    balance_type = Column(String(20), default="debit")
    current_balance = Column(Float, default=0.0)
    gstin = Column(String(20), nullable=True)
    pan = Column(String(20), nullable=True)
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    state_code = Column(String(10), nullable=True)
    pincode = Column(String(20), nullable=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    credit_limit = Column(Float, default=0.0)
    credit_days = Column(Integer, default=0)
    is_party = Column(Boolean, default=False)
    is_system = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)


class Voucher(Base, TimestampMixin):
    __tablename__ = "vouchers"

    id = Column(String, primary_key=True)
    voucher_type = Column(String(50), nullable=False, index=True)
    voucher_number = Column(String(100), nullable=False, index=True)
    voucher_date = Column(String(20), nullable=False, index=True)
    branch_id = Column(String, nullable=True, index=True)
    entries = Column(JSON, default=list)
    narration = Column(Text, nullable=True)
    reference_number = Column(String(100), nullable=True)
    reference_type = Column(String(100), nullable=True)
    reference_id = Column(String, nullable=True)
    is_reversal = Column(Boolean, default=False)
    reversed_voucher_id = Column(String, nullable=True)
    reversed_by = Column(String, nullable=True)
    total_debit = Column(Float, default=0.0)
    total_credit = Column(Float, default=0.0)
    status = Column(String(50), default="approved")
    is_approved = Column(Boolean, default=True)
    created_by = Column(String(100), nullable=True)
    modified_by = Column(String(100), nullable=True)


class LedgerTransaction(Base, TimestampMixin):
    __tablename__ = "ledger_transactions"

    id = Column(String, primary_key=True)
    ledger_id = Column(String, nullable=False, index=True)
    voucher_id = Column(String, nullable=False, index=True)
    voucher_number = Column(String(100), nullable=False)
    voucher_type = Column(String(50), nullable=True)
    voucher_date = Column(String(20), nullable=False, index=True)
    branch_id = Column(String, nullable=True, index=True)
    debit = Column(Float, default=0.0)
    credit = Column(Float, default=0.0)
    entry_type = Column(String(20), nullable=True)
    amount = Column(Float, default=0.0)
    balance = Column(Float, default=0.0)
    narration = Column(Text, nullable=True)


class Item(Base, TimestampMixin):
    __tablename__ = "items"

    id = Column(String, primary_key=True)
    code = Column(String(100), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    print_name = Column(String(255), nullable=True)
    category = Column(String(100), nullable=True, index=True)
    hsn_code = Column(String(20), nullable=True)
    hsn = Column(String(20), nullable=True)
    unit = Column(String(50), nullable=True)
    alternate_unit = Column(String(50), nullable=True)
    conversion_factor = Column(Float, default=1.0)
    gst_rate = Column(Float, default=0.0)
    cess_rate = Column(Float, default=0.0)
    cost_price = Column(Float, default=0.0)
    selling_price = Column(Float, default=0.0)
    mrp = Column(Float, nullable=True)
    min_stock = Column(Float, default=0.0)
    max_stock = Column(Float, default=0.0)
    reorder_level = Column(Float, default=0.0)
    opening_stock = Column(Float, default=0.0)
    is_batch_wise = Column(Boolean, default=True)
    is_expiry_tracking = Column(Boolean, default=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)


class StockBatch(Base, TimestampMixin):
    __tablename__ = "stock_batches"

    id = Column(String, primary_key=True)
    item_id = Column(String, nullable=False, index=True)
    branch_id = Column(String, nullable=False, index=True)
    godown_id = Column(String, nullable=False, index=True)
    batch_number = Column(String(100), nullable=False, index=True)
    quantity = Column(Float, default=0.0)
    remaining_quantity = Column(Float, default=0.0)
    unit_cost = Column(Float, default=0.0)
    purchase_date = Column(String(20), nullable=True, index=True)
    expiry_date = Column(String(20), nullable=True, index=True)
    mfg_date = Column(String(20), nullable=True)
    supplier_id = Column(String, nullable=True)
    reference_type = Column(String(100), nullable=True)
    reference_id = Column(String, nullable=True)
    reference_number = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)


class StockTransaction(Base, TimestampMixin):
    __tablename__ = "stock_transactions"

    id = Column(String, primary_key=True)
    item_id = Column(String, nullable=False, index=True)
    branch_id = Column(String, nullable=False, index=True)
    godown_id = Column(String, nullable=False, index=True)
    transaction_type = Column(String(100), nullable=False)
    quantity = Column(Float, default=0.0)
    unit_cost = Column(Float, default=0.0)
    total_cost = Column(Float, default=0.0)
    batch_id = Column(String, nullable=True)
    batch_number = Column(String(100), nullable=True)
    reference_type = Column(String(100), nullable=True)
    reference_id = Column(String, nullable=True)
    reference_number = Column(String(100), nullable=True)
    transaction_date = Column(String(20), nullable=True, index=True)
    narration = Column(Text, nullable=True)
    running_qty = Column(Float, default=0.0)
    running_value = Column(Float, default=0.0)


class StockAdjustment(Base, TimestampMixin):
    __tablename__ = "stock_adjustments"

    id = Column(String, primary_key=True)
    adjustment_number = Column(String(100), nullable=True, index=True)
    branch_id = Column(String, nullable=False, index=True)
    godown_id = Column(String, nullable=False, index=True)
    adjustment_date = Column(String(20), nullable=False, index=True)
    reason = Column(Text, nullable=True)
    items = Column(JSON, default=list)
    narration = Column(Text, nullable=True)
    total_shortage = Column(Float, default=0.0)
    total_excess = Column(Float, default=0.0)
    net_value = Column(Float, default=0.0)
    status = Column(String(50), default="completed")
    created_by = Column(String(100), nullable=True)


class InterBranchTransfer(Base, TimestampMixin):
    __tablename__ = "inter_branch_transfers"

    id = Column(String, primary_key=True)
    transfer_number = Column(String(100), nullable=True, index=True)
    from_branch_id = Column(String, nullable=False, index=True)
    to_branch_id = Column(String, nullable=False, index=True)
    from_godown_id = Column(String, nullable=False)
    to_godown_id = Column(String, nullable=False)
    transfer_date = Column(String(20), nullable=False, index=True)
    items = Column(JSON, default=list)
    narration = Column(Text, nullable=True)
    total_quantity = Column(Float, default=0.0)
    total_value = Column(Float, default=0.0)
    status = Column(String(50), default="completed")
    created_by = Column(String(100), nullable=True)


class ManualStockOutward(Base, TimestampMixin):
    __tablename__ = "manual_stock_outwards"

    id = Column(String, primary_key=True)
    outward_number = Column(String(100), nullable=False, index=True)
    branch_id = Column(String, nullable=False, index=True)
    godown_id = Column(String, nullable=False, index=True)
    item_id = Column(String, nullable=False, index=True)
    item_name = Column(String(255), nullable=True)
    quantity = Column(Float, default=0.0)
    transaction_date = Column(String(20), nullable=False, index=True)
    remarks = Column(Text, nullable=True)
    created_by = Column(String(100), nullable=True)
    stock_result = Column(Text, nullable=True)


class Customer(Base, TimestampMixin):
    __tablename__ = "customers"

    id = Column(String, primary_key=True)
    name = Column(String(255), nullable=False, index=True)
    address = Column(Text, nullable=True)
    gstin = Column(String(20), nullable=True, index=True)
    pan = Column(String(20), nullable=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    credit_limit = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)


class Supplier(Base, TimestampMixin):
    __tablename__ = "suppliers"

    id = Column(String, primary_key=True)
    name = Column(String(255), nullable=False, index=True)
    address = Column(Text, nullable=True)
    gstin = Column(String(20), nullable=True, index=True)
    pan = Column(String(20), nullable=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)


class HSNMaster(Base, TimestampMixin):
    __tablename__ = "hsn_master"

    id = Column(String, primary_key=True)
    hsn_code = Column(String(20), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=False)
    gst_rate = Column(Float, default=0.0)
    cess_rate = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)


class PurchaseOrder(Base, TimestampMixin):
    __tablename__ = "purchase_orders"

    id = Column(String, primary_key=True)
    order_number = Column(String(100), nullable=False, index=True)
    branch_id = Column(String, nullable=False, index=True)
    supplier_id = Column(String, nullable=True)
    supplier_name = Column(String(255), nullable=False)
    supplier_address = Column(Text, nullable=True)
    supplier_gstin = Column(String(20), nullable=True)
    supplier_state = Column(String(100), nullable=True)
    supplier_state_code = Column(String(10), nullable=True)
    order_date = Column(String(20), nullable=False, index=True)
    expected_date = Column(String(20), nullable=True)
    items = Column(JSON, default=list)
    subtotal = Column(Float, default=0.0)
    discount_amount = Column(Float, default=0.0)
    taxable_amount = Column(Float, default=0.0)
    tax_amount = Column(Float, default=0.0)
    round_off = Column(Float, default=0.0)
    grand_total = Column(Float, default=0.0)
    notes = Column(Text, nullable=True)
    status = Column(String(50), default="pending")
    created_by = Column(String(100), nullable=True)


class PurchaseInvoice(Base, TimestampMixin):
    __tablename__ = "purchase_invoices"

    id = Column(String, primary_key=True)
    invoice_number = Column(String(100), nullable=False, index=True)
    branch_id = Column(String, nullable=False, index=True)
    supply_type = Column(String(50), nullable=True)
    supplier_id = Column(String, nullable=True)
    supplier_name = Column(String(255), nullable=False)
    supplier_address = Column(Text, nullable=True)
    supplier_gstin = Column(String(20), nullable=True)
    supplier_state = Column(String(100), nullable=True)
    supplier_state_code = Column(String(10), nullable=True)
    supplier_invoice_number = Column(String(100), nullable=True)
    supplier_invoice_date = Column(String(20), nullable=True)
    invoice_date = Column(String(20), nullable=False, index=True)
    purchase_order_id = Column(String, nullable=True)
    items = Column(JSON, default=list)
    subtotal = Column(Float, default=0.0)
    discount_amount = Column(Float, default=0.0)
    taxable_amount = Column(Float, default=0.0)
    cgst_amount = Column(Float, default=0.0)
    sgst_amount = Column(Float, default=0.0)
    igst_amount = Column(Float, default=0.0)
    cess_amount = Column(Float, default=0.0)
    round_off = Column(Float, default=0.0)
    grand_total = Column(Float, default=0.0)
    is_reverse_charge = Column(Boolean, default=False)
    tds_rate = Column(Float, default=0.0)
    tds_amount = Column(Float, default=0.0)
    net_payable = Column(Float, default=0.0)
    notes = Column(Text, nullable=True)
    voucher_id = Column(String, nullable=True)
    status = Column(String(50), default="completed")
    paid_amount = Column(Float, default=0.0)
    balance_amount = Column(Float, default=0.0)
    created_by = Column(String(100), nullable=True)


class PurchaseReturn(Base, TimestampMixin):
    __tablename__ = "purchase_returns"

    id = Column(String, primary_key=True)
    return_number = Column(String(100), nullable=False, index=True)
    branch_id = Column(String, nullable=False, index=True)
    purchase_invoice_id = Column(String, nullable=False)
    purchase_invoice_number = Column(String(100), nullable=True)
    supplier_id = Column(String, nullable=True)
    supplier_name = Column(String(255), nullable=False)
    supplier_gstin = Column(String(20), nullable=True)
    return_date = Column(String(20), nullable=False, index=True)
    items = Column(JSON, default=list)
    subtotal = Column(Float, default=0.0)
    taxable_amount = Column(Float, default=0.0)
    cgst_amount = Column(Float, default=0.0)
    sgst_amount = Column(Float, default=0.0)
    igst_amount = Column(Float, default=0.0)
    cess_amount = Column(Float, default=0.0)
    round_off = Column(Float, default=0.0)
    grand_total = Column(Float, default=0.0)
    reason = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    voucher_id = Column(String, nullable=True)
    status = Column(String(50), default="completed")
    created_by = Column(String(100), nullable=True)


class LegacyDocument(Base, TimestampMixin):
    __tablename__ = "legacy_documents"
    __table_args__ = (UniqueConstraint("collection", "doc_id", name="uq_legacy_collection_doc_id"),)

    pk = Column(Integer, primary_key=True, autoincrement=True)
    collection = Column(String(100), nullable=False, index=True)
    doc_id = Column(String(100), nullable=False, index=True)
    data = Column(JSON, nullable=False, default=dict)
