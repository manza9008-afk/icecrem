from typing import Dict, List

def calculate_gst(amount: float, gst_rate: float, customer_state: str, company_state: str = "Gujarat") -> Dict[str, float]:
    """Calculate GST breakdown"""
    gst_amount = (amount * gst_rate) / 100
    
    if customer_state == company_state:
        # Intra-state: CGST + SGST
        return {
            "cgst": gst_amount / 2,
            "sgst": gst_amount / 2,
            "igst": 0,
            "total_tax": gst_amount
        }
    else:
        # Inter-state: IGST
        return {
            "cgst": 0,
            "sgst": 0,
            "igst": gst_amount,
            "total_tax": gst_amount
        }

def format_gstr1_b2b(invoices: List[dict]) -> List[dict]:
    """Format B2B invoices for GSTR-1"""
    b2b_data = {}
    
    for invoice in invoices:
        ctin = invoice.get("customer_gstin", "")
        if not ctin:
            continue
        
        if ctin not in b2b_data:
            b2b_data[ctin] = []
        
        items_data = []
        for item in invoice.get("items", []):
            items_data.append({
                "num": len(items_data) + 1,
                "itm_det": {
                    "rt": item["gst_rate"],
                    "txval": item["amount"],
                    "iamt": item.get("igst", 0),
                    "camt": item.get("cgst", 0),
                    "samt": item.get("sgst", 0)
                }
            })
        
        b2b_data[ctin].append({
            "inum": invoice["invoice_number"],
            "idt": invoice["invoice_date"],
            "val": invoice["grand_total"],
            "pos": "24",  # Gujarat
            "rchrg": "N",
            "inv_typ": "R",
            "itms": items_data
        })
    
    return [{"ctin": k, "inv": v} for k, v in b2b_data.items()]

def generate_hsn_summary(invoices: List[dict]) -> Dict[str, dict]:
    """Generate HSN summary for GSTR-1"""
    hsn_data = {}
    
    for invoice in invoices:
        for item in invoice.get("items", []):
            hsn = item.get("hsn", "")
            if hsn not in hsn_data:
                hsn_data[hsn] = {
                    "hsn_sc": hsn,
                    "desc": item.get("item_name", ""),
                    "uqc": "PCS",
                    "qty": 0,
                    "val": 0,
                    "txval": 0,
                    "iamt": 0,
                    "camt": 0,
                    "samt": 0
                }
            
            hsn_data[hsn]["qty"] += item.get("quantity", 0)
            hsn_data[hsn]["val"] += item.get("amount", 0)
            hsn_data[hsn]["txval"] += item.get("amount", 0)
            hsn_data[hsn]["iamt"] += item.get("igst", 0)
            hsn_data[hsn]["camt"] += item.get("cgst", 0)
            hsn_data[hsn]["samt"] += item.get("sgst", 0)
    
    return hsn_data
