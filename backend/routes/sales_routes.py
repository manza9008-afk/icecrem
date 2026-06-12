"""
HOOREN ERP - Sales Routes
Quotation, Sales Order, Delivery Challan, Sales Invoice, Sales Return
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime, timezone
import uuid

router = APIRouter(prefix="/api/sales", tags=["sales"])

from server import db
from utils import get_current_user
from services.inventory_service import consume_stock_fifo, create_stock_batch
from services.accounting_service import post_to_ledgers, get_next_voucher_number
from services.gst_service import calculate_gst_breakup, determine_supply_type


async def get_next_document_number(prefix: str, collection: str) -> str:
    """Generate next document number"""
    last_doc = await db[collection].find_one(sort=[("created_at", -1)])
    
    if last_doc:
        try:
            parts = last_doc.get(f"{prefix.lower()}_number", "").split("/")
            last_num = int(parts[-1])
            new_num = last_num + 1
        except:
            new_num = 1
    else:
        new_num = 1
    
    return f"{prefix}/2025-26/{new_num:05d}"


def convert_amount_to_words(amount: float) -> str:
    """Convert amount to words"""
    ones = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine',
            'Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen',
            'Seventeen', 'Eighteen', 'Nineteen']
    tens = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety']
    
    def num_to_words(n):
        if n < 20:
            return ones[n]
        elif n < 100:
            return tens[n // 10] + (' ' + ones[n % 10] if n % 10 else '')
        elif n < 1000:
            return ones[n // 100] + ' Hundred' + (' and ' + num_to_words(n % 100) if n % 100 else '')
        elif n < 100000:
            return num_to_words(n // 1000) + ' Thousand' + (' ' + num_to_words(n % 1000) if n % 1000 else '')
        elif n < 10000000:
            return num_to_words(n // 100000) + ' Lakh' + (' ' + num_to_words(n % 100000) if n % 100000 else '')
        else:
            return num_to_words(n // 10000000) + ' Crore' + (' ' + num_to_words(n % 10000000) if n % 10000000 else '')
    
    rupees = int(amount)
    paise = int((amount - rupees) * 100)
    
    result = 'Rupees ' + num_to_words(rupees)
    if paise:
        result += ' and ' + num_to_words(paise) + ' Paise'
    result += ' Only'
    
    return result


# ==================== QUOTATIONS ====================

@router.get("/quotations")
async def get_quotations(
    branch_id: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get quotations"""
    query = {}
    if branch_id:
        query["branch_id"] = branch_id
    if status:
        query["status"] = status
    
    date_query = {}
    if start_date:
        date_query["$gte"] = start_date
    if end_date:
        date_query["$lte"] = end_date
    if date_query:
        query["quotation_date"] = date_query
    
    quotations = await db.quotations.find(query, {"_id": 0}).sort("quotation_date", -1).to_list(1000)
    return quotations


@router.get("/quotations/{quotation_id}")
async def get_quotation(quotation_id: str, current_user: dict = Depends(get_current_user)):
    """Get quotation details"""
    quotation = await db.quotations.find_one({"id": quotation_id}, {"_id": 0})
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    return quotation


@router.post("/quotations")
async def create_quotation(quotation_data: dict, current_user: dict = Depends(get_current_user)):
    """Create a new quotation"""
    quotation_number = await get_next_document_number("QTN", "quotations")
    
    quotation_doc = {
        "id": str(uuid.uuid4()),
        **quotation_data,
        "quotation_number": quotation_number,
        "status": "pending",
        "created_by": current_user["username"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.quotations.insert_one(quotation_doc)
    quotation_doc.pop("_id", None)
    return quotation_doc


@router.put("/quotations/{quotation_id}")
async def update_quotation(
    quotation_id: str,
    quotation_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Update quotation"""
    existing = await db.quotations.find_one({"id": quotation_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Quotation not found")
    
    if existing.get("status") == "converted":
        raise HTTPException(status_code=400, detail="Cannot modify converted quotation")
    
    quotation_data["modified_at"] = datetime.now(timezone.utc).isoformat()
    await db.quotations.update_one({"id": quotation_id}, {"$set": quotation_data})
    
    return {"message": "Quotation updated"}


# ==================== SALES ORDERS ====================

@router.get("/orders")
async def get_sales_orders(
    branch_id: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get sales orders"""
    query = {}
    if branch_id:
        query["branch_id"] = branch_id
    if status:
        query["status"] = status
    
    date_query = {}
    if start_date:
        date_query["$gte"] = start_date
    if end_date:
        date_query["$lte"] = end_date
    if date_query:
        query["order_date"] = date_query
    
    orders = await db.sales_orders.find(query, {"_id": 0}).sort("order_date", -1).to_list(1000)
    return orders


@router.get("/orders/{order_id}")
async def get_sales_order(order_id: str, current_user: dict = Depends(get_current_user)):
    """Get sales order details"""
    order = await db.sales_orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Sales order not found")
    return order


@router.post("/orders")
async def create_sales_order(order_data: dict, current_user: dict = Depends(get_current_user)):
    """Create sales order"""
    order_number = await get_next_document_number("SO", "sales_orders")
    
    # Initialize pending quantities
    for item in order_data.get("items", []):
        item["delivered_qty"] = 0
        item["pending_qty"] = item["quantity"]
    
    order_doc = {
        "id": str(uuid.uuid4()),
        **order_data,
        "order_number": order_number,
        "status": "pending",
        "created_by": current_user["username"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.sales_orders.insert_one(order_doc)
    
    # Update quotation status if linked
    if order_data.get("quotation_id"):
        await db.quotations.update_one(
            {"id": order_data["quotation_id"]},
            {"$set": {"status": "converted"}}
        )
    
    order_doc.pop("_id", None)
    return order_doc


# ==================== DELIVERY CHALLANS ====================

@router.get("/challans")
async def get_delivery_challans(
    branch_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get delivery challans"""
    query = {}
    if branch_id:
        query["branch_id"] = branch_id
    
    date_query = {}
    if start_date:
        date_query["$gte"] = start_date
    if end_date:
        date_query["$lte"] = end_date
    if date_query:
        query["delivery_date"] = date_query
    
    challans = await db.delivery_challans.find(query, {"_id": 0}).sort("delivery_date", -1).to_list(1000)
    return challans


@router.post("/challans")
async def create_delivery_challan(challan_data: dict, current_user: dict = Depends(get_current_user)):
    """Create delivery challan (updates stock)"""
    challan_number = await get_next_document_number("DC", "delivery_challans")
    
    # Validate sales order
    order = await db.sales_orders.find_one({"id": challan_data["sales_order_id"]})
    if not order:
        raise HTTPException(status_code=404, detail="Sales order not found")
    
    # Process each item - consume from stock
    for item in challan_data.get("items", []):
        result = await consume_stock_fifo(
            db, item["item_id"], challan_data["branch_id"],
            item["godown_id"], item["quantity"],
            "delivery_challan", challan_data["sales_order_id"],
            challan_number, challan_data["delivery_date"]
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=400,
                detail=f"Stock error for {item['item_name']}: {result['error']}"
            )
    
    challan_doc = {
        "id": str(uuid.uuid4()),
        **challan_data,
        "challan_number": challan_number,
        "status": "delivered",
        "created_by": current_user["username"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.delivery_challans.insert_one(challan_doc)
    
    # Update sales order delivery quantities
    for item in challan_data.get("items", []):
        await db.sales_orders.update_one(
            {"id": challan_data["sales_order_id"], "items.item_id": item["item_id"]},
            {
                "$inc": {
                    "items.$.delivered_qty": item["quantity"],
                    "items.$.pending_qty": -item["quantity"]
                }
            }
        )
    
    # Check if order is fully delivered
    updated_order = await db.sales_orders.find_one({"id": challan_data["sales_order_id"]})
    all_delivered = all(i["pending_qty"] <= 0 for i in updated_order.get("items", []))
    
    if all_delivered:
        await db.sales_orders.update_one(
            {"id": challan_data["sales_order_id"]},
            {"$set": {"status": "completed"}}
        )
    else:
        await db.sales_orders.update_one(
            {"id": challan_data["sales_order_id"]},
            {"$set": {"status": "partial"}}
        )
    
    challan_doc.pop("_id", None)
    return challan_doc


# ==================== SALES INVOICES ====================

@router.get("/invoices")
async def get_sales_invoices(
    branch_id: Optional[str] = None,
    invoice_type: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get sales invoices"""
    query = {}
    if branch_id:
        query["branch_id"] = branch_id
    if invoice_type:
        query["invoice_type"] = invoice_type
    if status:
        query["status"] = status
    
    date_query = {}
    if start_date:
        date_query["$gte"] = start_date
    if end_date:
        date_query["$lte"] = end_date
    if date_query:
        query["invoice_date"] = date_query
    
    invoices = await db.sales_invoices.find(query, {"_id": 0}).sort("invoice_date", -1).to_list(1000)
    return invoices


@router.get("/invoices/{invoice_id}")
async def get_sales_invoice(invoice_id: str, current_user: dict = Depends(get_current_user)):
    """Get sales invoice details"""
    invoice = await db.sales_invoices.find_one({"id": invoice_id}, {"_id": 0})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.post("/invoices")
async def create_sales_invoice(invoice_data: dict, current_user: dict = Depends(get_current_user)):
    """Create sales invoice with stock and accounting updates"""
    
    # Get company settings for state code
    company = await db.company_settings.find_one({})
    seller_state_code = company.get("state_code", "24") if company else "24"
    
    # Determine supply type
    buyer_state_code = invoice_data.get("customer_state_code", "24")
    supply_type = determine_supply_type(seller_state_code, buyer_state_code)
    invoice_data["supply_type"] = supply_type
    
    # Generate invoice number
    prefix = "GST" if invoice_data["invoice_type"] == "gst" else "KB"
    invoice_number = await get_next_document_number(prefix, "sales_invoices")
    
    # Calculate GST for each item
    for item in invoice_data.get("items", []):
        gst = calculate_gst_breakup(
            item["taxable_amount"],
            item["gst_rate"],
            supply_type,
            item.get("cess_rate", 0)
        )
        item.update({
            "cgst_amount": gst["cgst_amount"],
            "sgst_amount": gst["sgst_amount"],
            "igst_amount": gst["igst_amount"],
            "cess_amount": gst["cess_amount"],
            "total_amount": item["taxable_amount"] + gst["total_tax"]
        })
    
    # Recalculate totals
    invoice_data["cgst_amount"] = sum(i["cgst_amount"] for i in invoice_data["items"])
    invoice_data["sgst_amount"] = sum(i["sgst_amount"] for i in invoice_data["items"])
    invoice_data["igst_amount"] = sum(i["igst_amount"] for i in invoice_data["items"])
    invoice_data["cess_amount"] = sum(i.get("cess_amount", 0) for i in invoice_data["items"])
    
    tax_total = invoice_data["cgst_amount"] + invoice_data["sgst_amount"] + invoice_data["igst_amount"] + invoice_data["cess_amount"]
    invoice_data["grand_total"] = invoice_data["taxable_amount"] + tax_total - invoice_data.get("discount_amount", 0) + invoice_data.get("round_off", 0)
    
    # Amount in words
    invoice_data["amount_in_words"] = convert_amount_to_words(invoice_data["grand_total"])
    
    # Process stock (if not from delivery challan)
    if not invoice_data.get("delivery_challan_id"):
        for item in invoice_data.get("items", []):
            result = await consume_stock_fifo(
                db, item["item_id"], invoice_data["branch_id"],
                item["godown_id"], item["quantity"],
                "sales_invoice", invoice_number, invoice_number,
                invoice_data["invoice_date"]
            )
            
            if not result["success"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Stock error for {item['item_name']}: {result['error']}"
                )
    
    # Create invoice document
    invoice_doc = {
        "id": str(uuid.uuid4()),
        **invoice_data,
        "invoice_number": invoice_number,
        "paid_amount": 0,
        "balance_amount": invoice_data["grand_total"],
        "status": "completed",
        "created_by": current_user["username"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.sales_invoices.insert_one(invoice_doc)
    
    # Create accounting entries (only for GST invoices)
    if invoice_data["invoice_type"] == "gst":
        await create_sales_accounting_entry(db, invoice_doc, current_user["username"])
    
    invoice_doc.pop("_id", None)
    return invoice_doc


async def create_sales_accounting_entry(db, invoice: dict, username: str):
    """Create accounting voucher for sales invoice"""
    
    branch_id = invoice["branch_id"]
    
    # Find ledgers
    customer_ledger = await db.ledgers.find_one({
        "name": invoice["customer_name"],
        "branch_id": branch_id,
        "is_active": True
    })
    
    # Create customer ledger if doesn't exist
    if not customer_ledger:
        sundry_debtors = await db.account_groups.find_one({"code": "A0103"})
        if sundry_debtors:
            customer_ledger = {
                "id": str(uuid.uuid4()),
                "name": invoice["customer_name"],
                "account_group_id": sundry_debtors["id"],
                "branch_id": branch_id,
                "opening_balance": 0,
                "balance_type": "debit",
                "current_balance": 0,
                "gstin": invoice.get("customer_gstin"),
                "address": invoice.get("customer_address"),
                "state": invoice.get("customer_state"),
                "state_code": invoice.get("customer_state_code"),
                "is_party": True,
                "is_active": True,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.ledgers.insert_one(customer_ledger)
    
    sales_ledger = await db.ledgers.find_one({"name": "Sales Account", "branch_id": branch_id})
    cgst_output = await db.ledgers.find_one({"name": "CGST Output", "branch_id": branch_id})
    sgst_output = await db.ledgers.find_one({"name": "SGST Output", "branch_id": branch_id})
    igst_output = await db.ledgers.find_one({"name": "IGST Output", "branch_id": branch_id})
    
    entries = []
    
    # Debit: Customer
    if customer_ledger:
        entries.append({
            "ledger_id": customer_ledger["id"],
            "ledger_name": customer_ledger["name"],
            "debit": invoice["grand_total"],
            "credit": 0,
            "narration": f"Sales Invoice {invoice['invoice_number']}"
        })
    
    # Credit: Sales
    if sales_ledger:
        entries.append({
            "ledger_id": sales_ledger["id"],
            "ledger_name": sales_ledger["name"],
            "debit": 0,
            "credit": invoice["taxable_amount"],
            "narration": f"Sales Invoice {invoice['invoice_number']}"
        })
    
    # Credit: GST
    if invoice.get("cgst_amount", 0) > 0 and cgst_output:
        entries.append({
            "ledger_id": cgst_output["id"],
            "ledger_name": cgst_output["name"],
            "debit": 0,
            "credit": invoice["cgst_amount"],
            "narration": f"CGST on {invoice['invoice_number']}"
        })
    
    if invoice.get("sgst_amount", 0) > 0 and sgst_output:
        entries.append({
            "ledger_id": sgst_output["id"],
            "ledger_name": sgst_output["name"],
            "debit": 0,
            "credit": invoice["sgst_amount"],
            "narration": f"SGST on {invoice['invoice_number']}"
        })
    
    if invoice.get("igst_amount", 0) > 0 and igst_output:
        entries.append({
            "ledger_id": igst_output["id"],
            "ledger_name": igst_output["name"],
            "debit": 0,
            "credit": invoice["igst_amount"],
            "narration": f"IGST on {invoice['invoice_number']}"
        })
    
    if entries:
        voucher_number = await get_next_voucher_number(db, "sales", branch_id)
        
        total_debit = sum(e["debit"] for e in entries)
        total_credit = sum(e["credit"] for e in entries)
        
        voucher_doc = {
            "id": str(uuid.uuid4()),
            "voucher_type": "sales",
            "voucher_number": voucher_number,
            "voucher_date": invoice["invoice_date"],
            "branch_id": branch_id,
            "entries": entries,
            "narration": f"Sales Invoice {invoice['invoice_number']} - {invoice['customer_name']}",
            "reference_type": "sales_invoice",
            "reference_id": invoice["id"],
            "total_debit": total_debit,
            "total_credit": total_credit,
            "status": "approved",
            "created_by": username,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.vouchers.insert_one(voucher_doc)
        
        # Update invoice with voucher reference
        await db.sales_invoices.update_one(
            {"id": invoice["id"]},
            {"$set": {"voucher_id": voucher_doc["id"]}}
        )
        
        # Post to ledgers
        await post_to_ledgers(
            db, voucher_doc["id"], voucher_number, "sales",
            invoice["invoice_date"], branch_id, entries
        )


# ==================== SALES RETURNS ====================

@router.get("/returns")
async def get_sales_returns(
    branch_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get sales returns"""
    query = {}
    if branch_id:
        query["branch_id"] = branch_id
    
    date_query = {}
    if start_date:
        date_query["$gte"] = start_date
    if end_date:
        date_query["$lte"] = end_date
    if date_query:
        query["return_date"] = date_query
    
    returns = await db.sales_returns.find(query, {"_id": 0}).sort("return_date", -1).to_list(1000)
    return returns


@router.post("/returns")
async def create_sales_return(return_data: dict, current_user: dict = Depends(get_current_user)):
    """Create sales return (credit note)"""
    
    # Validate original invoice
    invoice = await db.sales_invoices.find_one({"id": return_data["sales_invoice_id"]})
    if not invoice:
        raise HTTPException(status_code=404, detail="Original invoice not found")
    
    return_number = await get_next_document_number("SRN", "sales_returns")
    
    # Add stock back
    for item in return_data.get("items", []):
        from services.inventory_service import create_stock_batch, get_next_batch_number
        
        batch_number = await get_next_batch_number(db, item["item_id"], return_data["branch_id"])
        await create_stock_batch(
            db, item["item_id"], return_data["branch_id"],
            item["godown_id"], batch_number, item["quantity"],
            item["rate"], return_data["return_date"],
            None, None, None, "sales_return", return_number, return_number
        )
    
    return_doc = {
        "id": str(uuid.uuid4()),
        **return_data,
        "return_number": return_number,
        "status": "completed",
        "created_by": current_user["username"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.sales_returns.insert_one(return_doc)
    
    # Create credit note accounting entry
    await create_credit_note_entry(db, return_doc, invoice, current_user["username"])
    
    return_doc.pop("_id", None)
    return return_doc


async def create_credit_note_entry(db, return_doc: dict, original_invoice: dict, username: str):
    """Create accounting entry for sales return (credit note)"""
    
    branch_id = return_doc["branch_id"]
    
    customer_ledger = await db.ledgers.find_one({
        "name": return_doc["customer_name"],
        "branch_id": branch_id
    })
    
    sales_ledger = await db.ledgers.find_one({"name": "Sales Account", "branch_id": branch_id})
    cgst_output = await db.ledgers.find_one({"name": "CGST Output", "branch_id": branch_id})
    sgst_output = await db.ledgers.find_one({"name": "SGST Output", "branch_id": branch_id})
    igst_output = await db.ledgers.find_one({"name": "IGST Output", "branch_id": branch_id})
    
    entries = []
    
    # Credit: Customer (reverse of sales)
    if customer_ledger:
        entries.append({
            "ledger_id": customer_ledger["id"],
            "ledger_name": customer_ledger["name"],
            "debit": 0,
            "credit": return_doc["grand_total"],
            "narration": f"Sales Return {return_doc['return_number']}"
        })
    
    # Debit: Sales
    if sales_ledger:
        entries.append({
            "ledger_id": sales_ledger["id"],
            "ledger_name": sales_ledger["name"],
            "debit": return_doc["taxable_amount"],
            "credit": 0,
            "narration": f"Sales Return {return_doc['return_number']}"
        })
    
    # Debit: GST
    if return_doc.get("cgst_amount", 0) > 0 and cgst_output:
        entries.append({
            "ledger_id": cgst_output["id"],
            "ledger_name": cgst_output["name"],
            "debit": return_doc["cgst_amount"],
            "credit": 0,
            "narration": f"CGST reversal on {return_doc['return_number']}"
        })
    
    if return_doc.get("sgst_amount", 0) > 0 and sgst_output:
        entries.append({
            "ledger_id": sgst_output["id"],
            "ledger_name": sgst_output["name"],
            "debit": return_doc["sgst_amount"],
            "credit": 0,
            "narration": f"SGST reversal on {return_doc['return_number']}"
        })
    
    if return_doc.get("igst_amount", 0) > 0 and igst_output:
        entries.append({
            "ledger_id": igst_output["id"],
            "ledger_name": igst_output["name"],
            "debit": return_doc["igst_amount"],
            "credit": 0,
            "narration": f"IGST reversal on {return_doc['return_number']}"
        })
    
    if entries:
        voucher_number = await get_next_voucher_number(db, "credit_note", branch_id)
        
        voucher_doc = {
            "id": str(uuid.uuid4()),
            "voucher_type": "credit_note",
            "voucher_number": voucher_number,
            "voucher_date": return_doc["return_date"],
            "branch_id": branch_id,
            "entries": entries,
            "narration": f"Credit Note {return_doc['return_number']} against {original_invoice['invoice_number']}",
            "reference_type": "sales_return",
            "reference_id": return_doc["id"],
            "total_debit": sum(e["debit"] for e in entries),
            "total_credit": sum(e["credit"] for e in entries),
            "status": "approved",
            "created_by": username,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.vouchers.insert_one(voucher_doc)
        
        await post_to_ledgers(
            db, voucher_doc["id"], voucher_number, "credit_note",
            return_doc["return_date"], branch_id, entries
        )
