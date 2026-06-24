"""
HOOREN ERP - GST Routes
GSTR-1, GSTR-3B, HSN Summary, GST Filing Export
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import List, Optional
from datetime import datetime, timezone
import uuid
import json

router = APIRouter(prefix="/api/gst", tags=["gst"])

from server import db
from utils import get_current_user
from services.gst_service import (
    generate_gstr1_report,
    generate_gstr3b_report,
    get_hsn_summary,
    export_gstr1_json,
    validate_gstin,
    calculate_input_tax_credit,
    STATE_CODES
)


# ==================== HSN MASTER ====================

@router.get("/hsn")
async def get_hsn_codes(
    search: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get HSN master codes"""
    query = {"is_active": True}
    if search:
        query["$or"] = [
            {"hsn_code": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}}
        ]
    
    hsn_codes = await db.hsn_master.find(query, {"_id": 0}).to_list(1000)
    return hsn_codes


@router.post("/hsn")
async def create_hsn_code(hsn_data: dict, current_user: dict = Depends(get_current_user)):
    """Create HSN code entry"""
    existing = await db.hsn_master.find_one({"hsn_code": hsn_data["hsn_code"]})
    if existing:
        raise HTTPException(status_code=400, detail="HSN code already exists")
    
    hsn_doc = {
        "id": str(uuid.uuid4()),
        **hsn_data,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.hsn_master.insert_one(hsn_doc)
    hsn_doc.pop("_id", None)
    return hsn_doc


@router.put("/hsn/{hsn_id}")
async def update_hsn_code(
    hsn_id: str,
    hsn_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Update HSN code"""
    existing = await db.hsn_master.find_one({"id": hsn_id})
    if not existing:
        raise HTTPException(status_code=404, detail="HSN code not found")
    
    await db.hsn_master.update_one({"id": hsn_id}, {"$set": hsn_data})
    return {"message": "HSN code updated"}


# ==================== STATE CODES ====================

@router.get("/state-codes")
async def get_state_codes(current_user: dict = Depends(get_current_user)):
    """Get all Indian state codes"""
    return [{"code": k, "name": v} for k, v in STATE_CODES.items()]


# ==================== GSTIN VALIDATION ====================

@router.post("/validate-gstin")
async def validate_gstin_endpoint(gstin: str, current_user: dict = Depends(get_current_user)):
    """Validate GSTIN format"""
    result = await validate_gstin(gstin)
    return result


# ==================== GSTR-1 REPORT ====================

@router.get("/gstr1")
async def get_gstr1(
    month: int,
    year: int,
    branch_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Generate GSTR-1 report data"""
    company = await db.company_settings.find_one({})
    if not company or not company.get("gstin"):
        raise HTTPException(status_code=400, detail="Company GSTIN not configured")
    
    report = await generate_gstr1_report(db, company["gstin"], month, year, branch_id)
    return report


@router.get("/gstr1/export")
async def export_gstr1(
    month: int,
    year: int,
    branch_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Export GSTR-1 as JSON for GST portal upload"""
    company = await db.company_settings.find_one({})
    if not company or not company.get("gstin"):
        raise HTTPException(status_code=400, detail="Company GSTIN not configured")
    
    report = await generate_gstr1_report(db, company["gstin"], month, year, branch_id)
    json_data = export_gstr1_json(report)
    
    return JSONResponse(
        content=json.loads(json_data),
        headers={
            "Content-Disposition": f"attachment; filename=GSTR1_{month:02d}{year}.json"
        }
    )


# ==================== GSTR-3B REPORT ====================

@router.get("/gstr3b")
async def get_gstr3b(
    month: int,
    year: int,
    branch_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Generate GSTR-3B summary report"""
    company = await db.company_settings.find_one({})
    if not company or not company.get("gstin"):
        raise HTTPException(status_code=400, detail="Company GSTIN not configured")
    
    report = await generate_gstr3b_report(db, company["gstin"], month, year, branch_id)
    return report


# ==================== HSN SUMMARY REPORT ====================

@router.get("/hsn-summary")
async def get_hsn_summary_report(
    month: int,
    year: int,
    report_type: str = "sales",  # sales or purchase
    branch_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get HSN-wise summary for sales or purchases"""
    result = await get_hsn_summary(db, month, year, branch_id, report_type)
    
    total_taxable = sum(r["taxable_value"] for r in result)
    total_tax = sum(r["total_tax"] for r in result)
    
    return {
        "month": month,
        "year": year,
        "report_type": report_type,
        "items": result,
        "totals": {
            "taxable_value": round(total_taxable, 2),
            "total_tax": round(total_tax, 2)
        }
    }


# ==================== INPUT TAX CREDIT ====================

@router.get("/itc")
async def get_input_tax_credit(
    month: int,
    year: int,
    branch_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Calculate available Input Tax Credit"""
    result = await calculate_input_tax_credit(db, branch_id, month, year)
    return result


# ==================== TAX LIABILITY SUMMARY ====================

@router.get("/tax-liability")
async def get_tax_liability(
    month: int,
    year: int,
    branch_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Calculate monthly tax liability"""
    
    # Calculate date range
    start_date = f"{year}-{month:02d}-01"
    if month == 12:
        end_date = f"{year + 1}-01-01"
    else:
        end_date = f"{year}-{month + 1:02d}-01"
    
    # Get sales GST
    sales_query = {
        "invoice_type": "gst",
        "invoice_date": {"$gte": start_date, "$lt": end_date},
        "status": "completed"
    }
    if branch_id:
        sales_query["branch_id"] = branch_id
    
    sales = await db.sales_invoices.find(sales_query, {"_id": 0}).to_list(10000)
    
    output_cgst = sum(s.get("cgst_amount", 0) for s in sales)
    output_sgst = sum(s.get("sgst_amount", 0) for s in sales)
    output_igst = sum(s.get("igst_amount", 0) for s in sales)
    output_cess = sum(s.get("cess_amount", 0) for s in sales)
    
    # Get purchase GST (ITC)
    purchase_query = {
        "invoice_date": {"$gte": start_date, "$lt": end_date},
        "status": "completed"
    }
    if branch_id:
        purchase_query["branch_id"] = branch_id
    
    purchases = await db.purchase_invoices.find(purchase_query, {"_id": 0}).to_list(10000)
    
    input_cgst = sum(p.get("cgst_amount", 0) for p in purchases if not p.get("is_reverse_charge"))
    input_sgst = sum(p.get("sgst_amount", 0) for p in purchases if not p.get("is_reverse_charge"))
    input_igst = sum(p.get("igst_amount", 0) for p in purchases if not p.get("is_reverse_charge"))
    input_cess = sum(p.get("cess_amount", 0) for p in purchases if not p.get("is_reverse_charge"))
    
    # Get sales returns (credit notes)
    returns_query = {
        "return_date": {"$gte": start_date, "$lt": end_date},
        "status": "completed"
    }
    if branch_id:
        returns_query["branch_id"] = branch_id
    
    sales_returns = await db.sales_returns.find(returns_query, {"_id": 0}).to_list(10000)
    
    return_cgst = sum(r.get("cgst_amount", 0) for r in sales_returns)
    return_sgst = sum(r.get("sgst_amount", 0) for r in sales_returns)
    return_igst = sum(r.get("igst_amount", 0) for r in sales_returns)
    
    # Net liability
    net_cgst = output_cgst - input_cgst - return_cgst
    net_sgst = output_sgst - input_sgst - return_sgst
    net_igst = output_igst - input_igst - return_igst
    net_cess = output_cess - input_cess
    
    return {
        "period": {"month": month, "year": year},
        "output_tax": {
            "cgst": round(output_cgst, 2),
            "sgst": round(output_sgst, 2),
            "igst": round(output_igst, 2),
            "cess": round(output_cess, 2),
            "total": round(output_cgst + output_sgst + output_igst + output_cess, 2)
        },
        "input_tax_credit": {
            "cgst": round(input_cgst, 2),
            "sgst": round(input_sgst, 2),
            "igst": round(input_igst, 2),
            "cess": round(input_cess, 2),
            "total": round(input_cgst + input_sgst + input_igst + input_cess, 2)
        },
        "credit_note_adjustment": {
            "cgst": round(return_cgst, 2),
            "sgst": round(return_sgst, 2),
            "igst": round(return_igst, 2)
        },
        "net_liability": {
            "cgst": round(max(0, net_cgst), 2),
            "sgst": round(max(0, net_sgst), 2),
            "igst": round(max(0, net_igst), 2),
            "cess": round(max(0, net_cess), 2),
            "total": round(max(0, net_cgst) + max(0, net_sgst) + max(0, net_igst) + max(0, net_cess), 2)
        },
        "itc_carry_forward": {
            "cgst": round(abs(min(0, net_cgst)), 2),
            "sgst": round(abs(min(0, net_sgst)), 2),
            "igst": round(abs(min(0, net_igst)), 2)
        }
    }


# ==================== REVERSE CHARGE REPORT ====================

@router.get("/reverse-charge")
async def get_reverse_charge_report(
    month: int,
    year: int,
    branch_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get reverse charge mechanism transactions"""
    
    start_date = f"{year}-{month:02d}-01"
    if month == 12:
        end_date = f"{year + 1}-01-01"
    else:
        end_date = f"{year}-{month + 1:02d}-01"
    
    query = {
        "is_reverse_charge": True,
        "invoice_date": {"$gte": start_date, "$lt": end_date},
        "status": "completed"
    }
    if branch_id:
        query["branch_id"] = branch_id
    
    invoices = await db.purchase_invoices.find(query, {"_id": 0}).to_list(1000)
    
    total_taxable = sum(inv["taxable_amount"] for inv in invoices)
    total_cgst = sum(inv.get("cgst_amount", 0) for inv in invoices)
    total_sgst = sum(inv.get("sgst_amount", 0) for inv in invoices)
    total_igst = sum(inv.get("igst_amount", 0) for inv in invoices)
    
    return {
        "period": {"month": month, "year": year},
        "invoices": invoices,
        "totals": {
            "taxable_value": round(total_taxable, 2),
            "cgst": round(total_cgst, 2),
            "sgst": round(total_sgst, 2),
            "igst": round(total_igst, 2),
            "total_tax": round(total_cgst + total_sgst + total_igst, 2)
        }
    }


# ==================== SEED HSN DATA ====================

@router.post("/seed-hsn")
async def seed_hsn_data(current_user: dict = Depends(get_current_user)):
    """Seed common HSN codes for food products"""
    
    hsn_codes = [
        {"hsn_code": "2105", "description": "Ice cream and other edible ice", "gst_rate": 18},
        {"hsn_code": "21050000", "description": "Ice cream and other edible ice, whether or not containing cocoa", "gst_rate": 18},
        {"hsn_code": "0401", "description": "Milk and cream, not concentrated", "gst_rate": 0},
        {"hsn_code": "0402", "description": "Milk and cream, concentrated or sweetened", "gst_rate": 5},
        {"hsn_code": "0403", "description": "Buttermilk, curdled milk and cream, yogurt", "gst_rate": 5},
        {"hsn_code": "0404", "description": "Whey", "gst_rate": 5},
        {"hsn_code": "0405", "description": "Butter and other fats derived from milk", "gst_rate": 12},
        {"hsn_code": "0406", "description": "Cheese and curd", "gst_rate": 12},
        {"hsn_code": "1704", "description": "Sugar confectionery (excluding cocoa)", "gst_rate": 18},
        {"hsn_code": "1806", "description": "Chocolate and food preparations containing cocoa", "gst_rate": 18},
        {"hsn_code": "1901", "description": "Malt extract, food preparations of flour", "gst_rate": 18},
        {"hsn_code": "1902", "description": "Pasta", "gst_rate": 12},
        {"hsn_code": "1904", "description": "Prepared foods obtained by swelling cereals", "gst_rate": 18},
        {"hsn_code": "1905", "description": "Bread, pastry, cakes, biscuits", "gst_rate": 18},
        {"hsn_code": "2007", "description": "Jams, fruit jellies, marmalades", "gst_rate": 12},
        {"hsn_code": "2009", "description": "Fruit juices", "gst_rate": 12},
        {"hsn_code": "2106", "description": "Food preparations not elsewhere specified", "gst_rate": 18},
        {"hsn_code": "2201", "description": "Waters, including mineral and aerated", "gst_rate": 18},
        {"hsn_code": "2202", "description": "Waters, flavoured or sweetened", "gst_rate": 28},
        {"hsn_code": "8418", "description": "Refrigerators, freezers", "gst_rate": 18},
        {"hsn_code": "4819", "description": "Cartons, boxes, paper packaging", "gst_rate": 18},
        {"hsn_code": "3923", "description": "Plastic packaging articles", "gst_rate": 18},
        {"hsn_code": "9954", "description": "Services - Restaurant", "gst_rate": 5},
        {"hsn_code": "9963", "description": "Services - Accommodation", "gst_rate": 12},
        {"hsn_code": "9965", "description": "Services - Transport", "gst_rate": 5},
        {"hsn_code": "9971", "description": "Services - Financial", "gst_rate": 18},
    ]
    
    inserted = 0
    for hsn in hsn_codes:
        existing = await db.hsn_master.find_one({"hsn_code": hsn["hsn_code"]})
        if not existing:
            hsn_doc = {
                "id": str(uuid.uuid4()),
                **hsn,
                "cess_rate": 0,
                "is_active": True,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.hsn_master.insert_one(hsn_doc)
            inserted += 1
    
    return {"message": f"Seeded {inserted} HSN codes", "total": len(hsn_codes)}
