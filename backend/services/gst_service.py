"""
HOOREN ERP - GST Services
GST calculations, GSTR-1, GSTR-3B report generation
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import json

DatabaseHandle = Any

# Indian State Codes
STATE_CODES = {
    "01": "Jammu & Kashmir", "02": "Himachal Pradesh", "03": "Punjab",
    "04": "Chandigarh", "05": "Uttarakhand", "06": "Haryana",
    "07": "Delhi", "08": "Rajasthan", "09": "Uttar Pradesh",
    "10": "Bihar", "11": "Sikkim", "12": "Arunachal Pradesh",
    "13": "Nagaland", "14": "Manipur", "15": "Mizoram",
    "16": "Tripura", "17": "Meghalaya", "18": "Assam",
    "19": "West Bengal", "20": "Jharkhand", "21": "Odisha",
    "22": "Chhattisgarh", "23": "Madhya Pradesh", "24": "Gujarat",
    "25": "Daman & Diu", "26": "Dadra & Nagar Haveli", "27": "Maharashtra",
    "28": "Andhra Pradesh (Old)", "29": "Karnataka", "30": "Goa",
    "31": "Lakshadweep", "32": "Kerala", "33": "Tamil Nadu",
    "34": "Puducherry", "35": "Andaman & Nicobar", "36": "Telangana",
    "37": "Andhra Pradesh", "38": "Ladakh"
}


def calculate_gst_breakup(
    taxable_amount: float,
    gst_rate: float,
    supply_type: str,  # "intra_state" or "inter_state"
    cess_rate: float = 0.0
) -> Dict[str, float]:
    """Calculate GST breakup based on supply type"""
    
    gst_amount = taxable_amount * (gst_rate / 100)
    cess_amount = taxable_amount * (cess_rate / 100)
    
    if supply_type == "inter_state":
        return {
            "cgst_rate": 0,
            "cgst_amount": 0,
            "sgst_rate": 0,
            "sgst_amount": 0,
            "igst_rate": gst_rate,
            "igst_amount": round(gst_amount, 2),
            "cess_rate": cess_rate,
            "cess_amount": round(cess_amount, 2),
            "total_tax": round(gst_amount + cess_amount, 2)
        }
    else:  # intra_state
        half_rate = gst_rate / 2
        half_amount = gst_amount / 2
        return {
            "cgst_rate": half_rate,
            "cgst_amount": round(half_amount, 2),
            "sgst_rate": half_rate,
            "sgst_amount": round(half_amount, 2),
            "igst_rate": 0,
            "igst_amount": 0,
            "cess_rate": cess_rate,
            "cess_amount": round(cess_amount, 2),
            "total_tax": round(gst_amount + cess_amount, 2)
        }


def determine_supply_type(seller_state_code: str, buyer_state_code: str) -> str:
    """Determine if supply is intra-state or inter-state"""
    if seller_state_code == buyer_state_code:
        return "intra_state"
    return "inter_state"


async def generate_gstr1_report(
    db: DatabaseHandle,
    gstin: str,
    month: int,
    year: int,
    branch_id: Optional[str] = None
) -> Dict[str, Any]:
    """Generate GSTR-1 report data"""
    
    # Calculate date range
    start_date = f"{year}-{month:02d}-01"
    if month == 12:
        end_date = f"{year + 1}-01-01"
    else:
        end_date = f"{year}-{month + 1:02d}-01"
    
    # Query GST invoices
    query = {
        "invoice_type": "gst",
        "invoice_date": {"$gte": start_date, "$lt": end_date},
        "status": "completed"
    }
    if branch_id:
        query["branch_id"] = branch_id
    
    invoices = await db.sales_invoices.find(query, {"_id": 0}).to_list(10000)
    
    # Separate B2B and B2C
    b2b_data = {}  # Grouped by customer GSTIN
    b2cs_data = {}  # Grouped by rate + supply type
    b2cl_data = {}  # Large B2C (>2.5L inter-state)
    hsn_summary = {}
    
    for invoice in invoices:
        customer_gstin = invoice.get("customer_gstin")
        supply_type = invoice.get("supply_type", "intra_state")
        
        # Process items for HSN summary
        for item in invoice["items"]:
            hsn = item["hsn_code"]
            if hsn not in hsn_summary:
                hsn_summary[hsn] = {
                    "hsn_sc": hsn,
                    "desc": item["item_name"][:30],
                    "uqc": "NOS",
                    "qty": 0,
                    "val": 0,
                    "txval": 0,
                    "camt": 0,
                    "samt": 0,
                    "iamt": 0,
                    "csamt": 0
                }
            hsn_summary[hsn]["qty"] += item["quantity"]
            hsn_summary[hsn]["val"] += item["total_amount"]
            hsn_summary[hsn]["txval"] += item["taxable_amount"]
            hsn_summary[hsn]["camt"] += item.get("cgst_amount", 0)
            hsn_summary[hsn]["samt"] += item.get("sgst_amount", 0)
            hsn_summary[hsn]["iamt"] += item.get("igst_amount", 0)
            hsn_summary[hsn]["csamt"] += item.get("cess_amount", 0)
        
        if customer_gstin:
            # B2B - Registered dealer
            if customer_gstin not in b2b_data:
                b2b_data[customer_gstin] = []
            
            # Group items by rate
            items_by_rate = {}
            for item in invoice["items"]:
                rate = item["gst_rate"]
                if rate not in items_by_rate:
                    items_by_rate[rate] = {
                        "rt": rate,
                        "txval": 0,
                        "camt": 0,
                        "samt": 0,
                        "iamt": 0,
                        "csamt": 0
                    }
                items_by_rate[rate]["txval"] += item["taxable_amount"]
                items_by_rate[rate]["camt"] += item.get("cgst_amount", 0)
                items_by_rate[rate]["samt"] += item.get("sgst_amount", 0)
                items_by_rate[rate]["iamt"] += item.get("igst_amount", 0)
                items_by_rate[rate]["csamt"] += item.get("cess_amount", 0)
            
            inv_date = invoice["invoice_date"][:10].replace("-", "/")
            parts = inv_date.split("/")
            formatted_date = f"{parts[2]}-{parts[1]}-{parts[0]}"
            
            b2b_data[customer_gstin].append({
                "inum": invoice["invoice_number"],
                "idt": formatted_date,
                "val": invoice["grand_total"],
                "pos": invoice.get("customer_state_code", "24"),
                "rchrg": "Y" if invoice.get("is_reverse_charge") else "N",
                "inv_typ": "R",
                "itms": [{"num": i + 1, "itm_det": v} for i, v in enumerate(items_by_rate.values())]
            })
        else:
            # B2C - Unregistered
            if supply_type == "inter_state" and invoice["grand_total"] > 250000:
                # B2CL - Large inter-state
                pos = invoice.get("customer_state_code", "24")
                if pos not in b2cl_data:
                    b2cl_data[pos] = []
                
                b2cl_data[pos].append({
                    "inum": invoice["invoice_number"],
                    "idt": invoice["invoice_date"][:10],
                    "val": invoice["grand_total"],
                    "txval": invoice["taxable_amount"],
                    "camt": invoice.get("cgst_amount", 0),
                    "samt": invoice.get("sgst_amount", 0),
                    "iamt": invoice.get("igst_amount", 0),
                    "csamt": invoice.get("cess_amount", 0)
                })
            else:
                # B2CS - Small
                sply_ty = "INTER" if supply_type == "inter_state" else "INTRA"
                pos = invoice.get("customer_state_code", "24")
                
                for item in invoice["items"]:
                    key = f"{sply_ty}_{pos}_{item['gst_rate']}"
                    if key not in b2cs_data:
                        b2cs_data[key] = {
                            "sply_ty": sply_ty,
                            "pos": pos,
                            "typ": "OE",
                            "rt": item["gst_rate"],
                            "txval": 0,
                            "camt": 0,
                            "samt": 0,
                            "iamt": 0,
                            "csamt": 0
                        }
                    b2cs_data[key]["txval"] += item["taxable_amount"]
                    b2cs_data[key]["camt"] += item.get("cgst_amount", 0)
                    b2cs_data[key]["samt"] += item.get("sgst_amount", 0)
                    b2cs_data[key]["iamt"] += item.get("igst_amount", 0)
                    b2cs_data[key]["csamt"] += item.get("cess_amount", 0)
    
    # Format B2B
    b2b_formatted = [
        {"ctin": ctin, "inv": invs}
        for ctin, invs in b2b_data.items()
    ]
    
    # Format B2CL
    b2cl_formatted = [
        {"pos": pos, "inv": invs}
        for pos, invs in b2cl_data.items()
    ]
    
    # Format HSN
    hsn_formatted = {
        "data": [
            {**v, "num": i + 1}
            for i, v in enumerate(hsn_summary.values())
        ]
    }
    
    return {
        "gstin": gstin,
        "fp": f"{month:02d}{year}",
        "b2b": b2b_formatted,
        "b2cs": list(b2cs_data.values()),
        "b2cl": b2cl_formatted,
        "cdnr": [],  # Credit/Debit notes - to be implemented
        "cdnur": [],
        "exp": [],
        "hsn": hsn_formatted
    }


async def generate_gstr3b_report(
    db: DatabaseHandle,
    gstin: str,
    month: int,
    year: int,
    branch_id: Optional[str] = None
) -> Dict[str, Any]:
    """Generate GSTR-3B summary report"""
    
    # Calculate date range
    start_date = f"{year}-{month:02d}-01"
    if month == 12:
        end_date = f"{year + 1}-01-01"
    else:
        end_date = f"{year}-{month + 1:02d}-01"
    
    # Initialize summary
    outward_taxable = {"txval": 0, "iamt": 0, "camt": 0, "samt": 0, "csamt": 0}
    outward_zero = {"txval": 0, "iamt": 0, "camt": 0, "samt": 0, "csamt": 0}
    outward_nil = {"txval": 0, "iamt": 0, "camt": 0, "samt": 0, "csamt": 0}
    outward_exempt = {"txval": 0, "iamt": 0, "camt": 0, "samt": 0, "csamt": 0}
    
    inward_reverse = {"txval": 0, "iamt": 0, "camt": 0, "samt": 0, "csamt": 0}
    
    eligible_itc = {"iamt": 0, "camt": 0, "samt": 0}
    ineligible_itc = {"iamt": 0, "camt": 0, "samt": 0}
    
    # Query sales invoices
    sales_query = {
        "invoice_type": "gst",
        "invoice_date": {"$gte": start_date, "$lt": end_date},
        "status": "completed"
    }
    if branch_id:
        sales_query["branch_id"] = branch_id
    
    sales = await db.sales_invoices.find(sales_query, {"_id": 0}).to_list(10000)
    
    for invoice in sales:
        for item in invoice["items"]:
            if item["gst_rate"] > 0:
                outward_taxable["txval"] += item["taxable_amount"]
                outward_taxable["camt"] += item.get("cgst_amount", 0)
                outward_taxable["samt"] += item.get("sgst_amount", 0)
                outward_taxable["iamt"] += item.get("igst_amount", 0)
                outward_taxable["csamt"] += item.get("cess_amount", 0)
            elif item["gst_rate"] == 0:
                outward_zero["txval"] += item["taxable_amount"]
    
    # Query purchase invoices for ITC
    purchase_query = {
        "invoice_date": {"$gte": start_date, "$lt": end_date},
        "status": "completed"
    }
    if branch_id:
        purchase_query["branch_id"] = branch_id
    
    purchases = await db.purchase_invoices.find(purchase_query, {"_id": 0}).to_list(10000)
    
    for invoice in purchases:
        if invoice.get("is_reverse_charge"):
            for item in invoice["items"]:
                inward_reverse["txval"] += item["taxable_amount"]
                inward_reverse["camt"] += item.get("cgst_amount", 0)
                inward_reverse["samt"] += item.get("sgst_amount", 0)
                inward_reverse["iamt"] += item.get("igst_amount", 0)
        else:
            for item in invoice["items"]:
                eligible_itc["camt"] += item.get("cgst_amount", 0)
                eligible_itc["samt"] += item.get("sgst_amount", 0)
                eligible_itc["iamt"] += item.get("igst_amount", 0)
    
    # Calculate net tax liability
    net_liability = {
        "camt": outward_taxable["camt"] - eligible_itc["camt"],
        "samt": outward_taxable["samt"] - eligible_itc["samt"],
        "iamt": outward_taxable["iamt"] - eligible_itc["iamt"]
    }
    
    return {
        "gstin": gstin,
        "ret_period": f"{month:02d}{year}",
        "outward_taxable_supplies": outward_taxable,
        "outward_zero_rated": outward_zero,
        "outward_nil_rated": outward_nil,
        "outward_exempt": outward_exempt,
        "inward_reverse_charge": inward_reverse,
        "inward_isd": {"txval": 0, "iamt": 0, "camt": 0, "samt": 0, "csamt": 0},
        "eligible_itc": eligible_itc,
        "ineligible_itc": ineligible_itc,
        "net_tax_liability": net_liability,
        "interest": 0,
        "late_fee": 0
    }


async def get_hsn_summary(
    db: DatabaseHandle,
    month: int,
    year: int,
    branch_id: Optional[str] = None,
    report_type: str = "sales"  # sales or purchase
) -> List[Dict[str, Any]]:
    """Get HSN-wise summary for sales or purchases"""
    
    # Calculate date range
    start_date = f"{year}-{month:02d}-01"
    if month == 12:
        end_date = f"{year + 1}-01-01"
    else:
        end_date = f"{year}-{month + 1:02d}-01"
    
    collection = "sales_invoices" if report_type == "sales" else "purchase_invoices"
    
    query = {
        "invoice_date": {"$gte": start_date, "$lt": end_date},
        "status": "completed"
    }
    if report_type == "sales":
        query["invoice_type"] = "gst"
    if branch_id:
        query["branch_id"] = branch_id
    
    invoices = await db[collection].find(query, {"_id": 0}).to_list(10000)
    
    hsn_summary = {}
    
    for invoice in invoices:
        for item in invoice["items"]:
            hsn = item["hsn_code"]
            if hsn not in hsn_summary:
                hsn_summary[hsn] = {
                    "hsn_code": hsn,
                    "description": item["item_name"][:50],
                    "quantity": 0,
                    "taxable_value": 0,
                    "cgst_amount": 0,
                    "sgst_amount": 0,
                    "igst_amount": 0,
                    "cess_amount": 0,
                    "total_tax": 0,
                    "total_value": 0
                }
            
            hsn_summary[hsn]["quantity"] += item["quantity"]
            hsn_summary[hsn]["taxable_value"] += item["taxable_amount"]
            hsn_summary[hsn]["cgst_amount"] += item.get("cgst_amount", 0)
            hsn_summary[hsn]["sgst_amount"] += item.get("sgst_amount", 0)
            hsn_summary[hsn]["igst_amount"] += item.get("igst_amount", 0)
            hsn_summary[hsn]["cess_amount"] += item.get("cess_amount", 0)
            hsn_summary[hsn]["total_tax"] += (
                item.get("cgst_amount", 0) + 
                item.get("sgst_amount", 0) + 
                item.get("igst_amount", 0) +
                item.get("cess_amount", 0)
            )
            hsn_summary[hsn]["total_value"] += item["total_amount"]
    
    # Round values
    for hsn_data in hsn_summary.values():
        for key in hsn_data:
            if isinstance(hsn_data[key], float):
                hsn_data[key] = round(hsn_data[key], 2)
    
    return list(hsn_summary.values())


def export_gstr1_json(gstr1_data: Dict[str, Any]) -> str:
    """Export GSTR-1 data as JSON for GST portal upload"""
    return json.dumps(gstr1_data, indent=2)


async def validate_gstin(gstin: str) -> Dict[str, Any]:
    """Validate GSTIN format"""
    
    if not gstin or len(gstin) != 15:
        return {"valid": False, "error": "GSTIN must be 15 characters"}
    
    # Basic format validation
    state_code = gstin[:2]
    if state_code not in STATE_CODES:
        return {"valid": False, "error": "Invalid state code"}
    
    # Check pattern
    import re
    pattern = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[0-9A-Z]{1}[Z]{1}[0-9A-Z]{1}$'
    if not re.match(pattern, gstin.upper()):
        return {"valid": False, "error": "Invalid GSTIN format"}
    
    return {
        "valid": True,
        "state_code": state_code,
        "state_name": STATE_CODES.get(state_code, "Unknown"),
        "pan": gstin[2:12]
    }


async def calculate_input_tax_credit(
    db: DatabaseHandle,
    branch_id: str,
    month: int,
    year: int
) -> Dict[str, Any]:
    """Calculate available Input Tax Credit"""
    
    start_date = f"{year}-{month:02d}-01"
    if month == 12:
        end_date = f"{year + 1}-01-01"
    else:
        end_date = f"{year}-{month + 1:02d}-01"
    
    query = {
        "branch_id": branch_id,
        "invoice_date": {"$gte": start_date, "$lt": end_date},
        "status": "completed"
    }
    
    purchases = await db.purchase_invoices.find(query, {"_id": 0}).to_list(10000)
    
    itc = {
        "cgst": 0,
        "sgst": 0,
        "igst": 0,
        "cess": 0,
        "total": 0
    }
    
    for invoice in purchases:
        if not invoice.get("is_reverse_charge"):
            itc["cgst"] += invoice.get("cgst_amount", 0)
            itc["sgst"] += invoice.get("sgst_amount", 0)
            itc["igst"] += invoice.get("igst_amount", 0)
            itc["cess"] += invoice.get("cess_amount", 0)
    
    itc["total"] = itc["cgst"] + itc["sgst"] + itc["igst"] + itc["cess"]
    
    # Round all values
    for key in itc:
        itc[key] = round(itc[key], 2)
    
    return itc
