"""
HOOREN ERP - Utility Functions
"""
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, Any, List
import os

SECRET_KEY = os.getenv("SECRET_KEY", "hooren-erp-secret-key-2025-secure")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480

security = HTTPBearer()


def create_access_token(data: dict):
    """Create JWT access token"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Validate JWT token and return current user"""
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        return {"username": username}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")


def format_currency(amount: float) -> str:
    """Format amount as Indian currency"""
    return f"₹{amount:,.2f}"


def format_date(date_str: str, output_format: str = "%d-%m-%Y") -> str:
    """Format date string"""
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.strftime(output_format)
    except:
        return date_str


def calculate_gst(subtotal: float, items: List[Any]) -> Dict[str, float]:
    """Calculate GST breakdown (legacy function for compatibility)"""
    cgst = 0
    sgst = 0
    igst = 0
    
    for item in items:
        if hasattr(item, 'gst_rate'):
            tax_rate = item.gst_rate / 100
            item_tax = item.amount * tax_rate
        else:
            tax_rate = item.get('gst_rate', 0) / 100
            item_tax = item.get('amount', 0) * tax_rate
        
        # For intra-state (Gujarat), split into CGST/SGST
        cgst += item_tax / 2
        sgst += item_tax / 2
    
    return {
        "cgst": round(cgst, 2),
        "sgst": round(sgst, 2),
        "igst": round(igst, 2),
        "total_tax": round(cgst + sgst + igst, 2)
    }


def generate_invoice_pdf(invoice: dict, company_settings: dict) -> bytes:
    """Generate PDF invoice (placeholder)"""
    # This will be implemented with reportlab
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    import io
    
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # Header
    p.setFont("Helvetica-Bold", 18)
    p.drawString(50, height - 50, company_settings.get("business_name", "HOOREN FOOD PRODUCTS"))
    
    p.setFont("Helvetica", 10)
    p.drawString(50, height - 70, company_settings.get("address", ""))
    p.drawString(50, height - 85, f"GSTIN: {company_settings.get('gstin', '')}")
    
    # Invoice details
    p.setFont("Helvetica-Bold", 14)
    invoice_title = "TAX INVOICE" if invoice.get("invoice_type") == "gst" else "INVOICE"
    p.drawString(400, height - 50, invoice_title)
    
    p.setFont("Helvetica", 10)
    p.drawString(400, height - 70, f"Invoice No: {invoice.get('invoice_number', '')}")
    p.drawString(400, height - 85, f"Date: {invoice.get('invoice_date', '')[:10]}")
    
    # Customer
    p.setFont("Helvetica-Bold", 11)
    p.drawString(50, height - 130, "Bill To:")
    p.setFont("Helvetica", 10)
    p.drawString(50, height - 145, invoice.get('customer_name', ''))
    p.drawString(50, height - 160, invoice.get('customer_address', ''))
    
    # Total
    p.setFont("Helvetica-Bold", 12)
    p.drawString(400, height - 200, f"Grand Total: ₹{invoice.get('grand_total', 0):,.2f}")
    
    p.showPage()
    p.save()
    
    buffer.seek(0)
    return buffer.getvalue()


def generate_excel_report(data: List[Dict], filename: str) -> bytes:
    """Generate Excel report (placeholder)"""
    return b"Excel data"


async def post_accounting_entry(db, transaction: Dict):
    """Post accounting entry (legacy function)"""
    # This is now handled by accounting_service
    pass
