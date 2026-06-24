from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
import uuid

# ==================== GST MODELS ====================

class TaxRateCreate(BaseModel):
    tax_name: str
    cgst_rate: float
    sgst_rate: float
    igst_rate: float
    cess_rate: float = 0
    is_active: bool = True

class TaxRate(TaxRateCreate):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class HSNMasterCreate(BaseModel):
    hsn_code: str
    description: str
    gst_rate: float
    is_active: bool = True

class HSNMaster(HSNMasterCreate):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class GSTR1B2BInvoice(BaseModel):
    inum: str  # Invoice number
    idt: str   # Invoice date
    val: float # Invoice value
    pos: str   # Place of supply
    rchrg: str = "N"  # Reverse charge
    inv_typ: str = "R"  # Invoice type
    itms: List[Dict]   # Items with HSN, tax details

class GSTR1B2B(BaseModel):
    ctin: str  # Customer GSTIN
    inv: List[GSTR1B2BInvoice]

class GSTR1Summary(BaseModel):
    gstin: str
    fp: str  # Filing period (MMYYYY)
    b2b: List[GSTR1B2B]
    b2cl: List[Dict]  # B2C Large
    b2cs: List[Dict]  # B2C Small
    hsn: Dict  # HSN summary

class GSTR3BSummary(BaseModel):
    gstin: str
    ret_period: str
    outward_taxable_supplies: float
    outward_tax: Dict[str, float]  # CGST, SGST, IGST
    inward_supplies: float
    input_tax_credit: Dict[str, float]
    net_tax_liability: Dict[str, float]
