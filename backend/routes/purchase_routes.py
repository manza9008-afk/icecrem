"""
HOOREN ERP - Purchase Routes
Purchase Order, Purchase Invoice, Purchase Return
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional, Any
from datetime import datetime, timezone
import uuid
import json

router = APIRouter(prefix="/api/purchase", tags=["purchase"])

from database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc, func

from utils import get_current_user
from db_models import (
    PurchaseOrder, PurchaseInvoice, PurchaseReturn,
    CompanySettings, Ledger, AccountGroup, Voucher, LedgerTransaction,
    Branch, Supplier, Item, StockBatch
)
from services.inventory_service import create_stock_batch, consume_stock_fifo, get_next_batch_number
# Re-implementing accounting services with SQLAlchemy until they are formally migrated
from services.accounting_service import get_next_voucher_number, post_to_ledgers
from services.gst_service import calculate_gst_breakup, determine_supply_type


def to_dict(obj):
    if not obj: return {}
    d = {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
    for k, v in d.items():
        if isinstance(v, datetime):
            d[k] = v.isoformat()
    return d


async def get_next_document_number(session: AsyncSession, prefix: str, model: Any) -> str:
    """Generate next document number using SQLAlchemy."""
    number_field_map = {
        PurchaseOrder: "order_number",
        PurchaseInvoice: "invoice_number",
        PurchaseReturn: "return_number",
    }
    number_field_name = number_field_map.get(model)
    if not number_field_name:
        raise ValueError("Unsupported model for document number generation")

    result = await session.execute(
        select(model).order_by(desc(model.created_at)).limit(1)
    )
    last_doc = result.scalar_one_or_none()

    new_num = 1
    if last_doc:
        try:
            number_field_value = getattr(last_doc, number_field_name, "")
            parts = number_field_value.split("/")
            last_num = int(parts[-1])
            new_num = last_num + 1
        except (ValueError, IndexError, TypeError):
            new_num = 1

    return f"{prefix}/2025-26/{new_num:05d}"


# ==================== PURCHASE ORDERS ====================

@router.get("/orders")
async def get_purchase_orders(
    branch_id: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get purchase orders"""
    query = select(PurchaseOrder)
    if branch_id:
        query = query.where(PurchaseOrder.branch_id == branch_id)
    if status:
        query = query.where(PurchaseOrder.status == status)
    if start_date:
        query = query.where(PurchaseOrder.order_date >= start_date)
    if end_date:
        query = query.where(PurchaseOrder.order_date <= end_date)

    query = query.order_by(desc(PurchaseOrder.order_date))
    result = await session.execute(query)
    orders = result.scalars().all()
    return [to_dict(o) for o in orders]


@router.get("/orders/{order_id}")
async def get_purchase_order(order_id: str, session: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Get purchase order details"""
    result = await session.execute(select(PurchaseOrder).where(PurchaseOrder.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return to_dict(order)


@router.post("/orders")
async def create_purchase_order(order_data: dict, session: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Create purchase order"""
    order_number = await get_next_document_number(session, "PO", PurchaseOrder)

    # Initialize quantities
    for item in order_data.get("items", []):
        item["received_qty"] = 0
        item["pending_qty"] = item["quantity"]

    new_order = PurchaseOrder(
        id=str(uuid.uuid4()),
        **order_data,
        order_number=order_number,
        status="pending",
        created_by=current_user["username"],
        created_at=datetime.now(timezone.utc)
    )

    session.add(new_order)
    await session.commit()
    return to_dict(new_order)


@router.put("/orders/{order_id}")
async def update_purchase_order(
    order_id: str,
    order_data: dict,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update purchase order"""
    result = await session.execute(select(PurchaseOrder).where(PurchaseOrder.id == order_id))
    existing = result.scalar_one_or_none()
    if not existing:
        raise HTTPException(status_code=404, detail="Purchase order not found")

    if existing.status == "completed":
        raise HTTPException(status_code=400, detail="Cannot modify completed order")

    for key, value in order_data.items():
        setattr(existing, key, value)

    existing.modified_at = datetime.now(timezone.utc)
    await session.commit()

    return {"message": "Purchase order updated"}


# ==================== PURCHASE INVOICES ====================

@router.get("/invoices")
async def get_purchase_invoices(
    branch_id: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get purchase invoices"""
    query = select(PurchaseInvoice)
    if branch_id:
        query = query.where(PurchaseInvoice.branch_id == branch_id)
    if status:
        query = query.where(PurchaseInvoice.status == status)
    if start_date:
        query = query.where(PurchaseInvoice.invoice_date >= start_date)
    if end_date:
        query = query.where(PurchaseInvoice.invoice_date <= end_date)

    query = query.order_by(desc(PurchaseInvoice.invoice_date))
    result = await session.execute(query)
    invoices = result.scalars().all()
    return [to_dict(i) for i in invoices]


@router.get("/invoices/{invoice_id}")
async def get_purchase_invoice(invoice_id: str, session: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Get purchase invoice details"""
    result = await session.execute(select(PurchaseInvoice).where(PurchaseInvoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return to_dict(invoice)


@router.post("/invoices")
async def create_purchase_invoice(invoice_data: dict, session: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Create purchase invoice with stock and accounting updates"""

    # Get company settings for state code
    comp_res = await session.execute(select(CompanySettings))
    company = comp_res.scalar_one_or_none()
    buyer_state_code = company.state_code if company else "24"

    invoice_data["supplier_name"] = invoice_data.get("supplier_name") or "Inventory Inward"
    invoice_data["supplier_address"] = invoice_data.get("supplier_address") or (company.address if company else "")
    invoice_data["supplier_state"] = invoice_data.get("supplier_state") or (company.state if company else "Gujarat")
    invoice_data["supplier_state_code"] = invoice_data.get("supplier_state_code") or buyer_state_code
    invoice_data["supplier_invoice_number"] = invoice_data.get("supplier_invoice_number") or "DIRECT-INWARD"
    invoice_data["supplier_invoice_date"] = invoice_data.get("supplier_invoice_date") or invoice_data.get("invoice_date")

    # Determine supply type
    seller_state_code = invoice_data.get("supplier_state_code", "24")
    supply_type = determine_supply_type(seller_state_code, buyer_state_code)
    invoice_data["supply_type"] = supply_type

    # Generate invoice number
    invoice_number = await get_next_document_number(session, "PI", PurchaseInvoice)

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

    # TDS calculation
    tds_amount = invoice_data.get("tds_amount", 0)
    invoice_data["net_payable"] = invoice_data["grand_total"] - tds_amount

    # Create stock batches
    for item in invoice_data.get("items", []):
        batch_number = item.get("batch_number")
        if not batch_number:
            batch_number = await get_next_batch_number(session, item["item_id"], invoice_data["branch_id"])

        unit_cost = item["taxable_amount"] / item["quantity"] if item["quantity"] > 0 else 0

        await create_stock_batch(
            session, item["item_id"], invoice_data["branch_id"],
            item["godown_id"], batch_number, item["quantity"],
            unit_cost, invoice_data["invoice_date"],
            item.get("expiry_date"), item.get("mfg_date"),
            invoice_data.get("supplier_id"),
            "purchase_invoice", invoice_number, invoice_number
        )

    # Create invoice document
    new_invoice = PurchaseInvoice(
        id=str(uuid.uuid4()),
        **invoice_data,
        invoice_number=invoice_number,
        paid_amount=0,
        balance_amount=invoice_data["net_payable"],
        status="completed",
        created_by=current_user["username"],
        created_at=datetime.now(timezone.utc)
    )

    session.add(new_invoice)
    await session.flush()

    # Create accounting entries
    invoice_dict = to_dict(new_invoice)
    await create_purchase_accounting_entry(session, invoice_dict, current_user["username"])

    # Update purchase order if linked
    if invoice_data.get("purchase_order_id"):
        po_res = await session.execute(select(PurchaseOrder).where(PurchaseOrder.id == invoice_data["purchase_order_id"]))
        po = po_res.scalar_one_or_none()
        if po:
            po_items = po.items or []
            all_received = True
            for inv_item in invoice_data.get("items", []):
                for po_item in po_items:
                    if po_item.get("item_id") == inv_item.get("item_id"):
                        po_item["received_qty"] = (po_item.get("received_qty", 0) or 0) + inv_item["quantity"]
                        po_item["pending_qty"] = (po_item.get("pending_qty", 0) or 0) - inv_item["quantity"]
                        break

            for po_item in po_items:
                if (po_item.get("pending_qty", 0) or 0) > 0:
                    all_received = False
                    break

            po.items = list(po_items)
            po.status = "completed" if all_received else "partial"
            session.add(po)

    await session.commit()
    return to_dict(new_invoice)


async def create_purchase_accounting_entry(session: AsyncSession, invoice: dict, username: str):
    """Create accounting voucher for purchase invoice"""

    branch_id = invoice["branch_id"]

    # Find or create supplier ledger
    res = await session.execute(select(Ledger).where(Ledger.name == invoice["supplier_name"], Ledger.branch_id == branch_id, Ledger.is_active == True))
    supplier_ledger = res.scalar_one_or_none()

    if not supplier_ledger:
        res = await session.execute(select(AccountGroup).where(AccountGroup.code == "L0101"))
        sundry_creditors = res.scalar_one_or_none()
        if sundry_creditors:
            supplier_ledger = Ledger(
                id=str(uuid.uuid4()), name=invoice["supplier_name"], account_group_id=sundry_creditors.id,
                branch_id=branch_id, opening_balance=0, balance_type="credit", current_balance=0,
                gstin=invoice.get("supplier_gstin"), address=invoice.get("supplier_address"),
                state=invoice.get("supplier_state"), state_code=invoice.get("supplier_state_code"),
                is_party=True, is_active=True, created_at=datetime.now(timezone.utc)
            )
            session.add(supplier_ledger)
            await session.flush()

    async def find_ledger(name):
        res = await session.execute(select(Ledger).where(Ledger.name == name, Ledger.branch_id == branch_id))
        return res.scalar_one_or_none()

    purchase_ledger = await find_ledger("Purchase Account")
    cgst_input = await find_ledger("CGST Input")
    sgst_input = await find_ledger("SGST Input")
    igst_input = await find_ledger("IGST Input")
    tds_payable = await find_ledger("TDS Payable")

    entries = []

    # Debit: Purchase
    if purchase_ledger:
        entries.append({
            "ledger_id": purchase_ledger.id,
            "ledger_name": purchase_ledger.name,
            "debit": invoice["taxable_amount"],
            "credit": 0,
            "narration": f"Purchase Invoice {invoice['invoice_number']}"
        })

    # Debit: GST Input
    if invoice.get("cgst_amount", 0) > 0 and cgst_input:
        entries.append({
            "ledger_id": cgst_input.id,
            "ledger_name": cgst_input.name,
            "debit": invoice["cgst_amount"],
            "credit": 0,
            "narration": f"CGST on {invoice['invoice_number']}"
        })

    if invoice.get("sgst_amount", 0) > 0 and sgst_input:
        entries.append({
            "ledger_id": sgst_input.id,
            "ledger_name": sgst_input.name,
            "debit": invoice["sgst_amount"],
            "credit": 0,
            "narration": f"SGST on {invoice['invoice_number']}"
        })

    if invoice.get("igst_amount", 0) > 0 and igst_input:
        entries.append({
            "ledger_id": igst_input.id,
            "ledger_name": igst_input.name,
            "debit": invoice["igst_amount"],
            "credit": 0,
            "narration": f"IGST on {invoice['invoice_number']}"
        })

    # Credit: Supplier
    if supplier_ledger:
        entries.append({
            "ledger_id": supplier_ledger.id,
            "ledger_name": supplier_ledger.name,
            "debit": 0,
            "credit": invoice["grand_total"],
            "narration": f"Purchase Invoice {invoice['invoice_number']}"
        })

    # Credit: TDS Payable (if applicable)
    if invoice.get("tds_amount", 0) > 0 and tds_payable:
        entries.append({
            "ledger_id": tds_payable.id,
            "ledger_name": tds_payable.name,
            "debit": 0,
            "credit": invoice["tds_amount"],
            "narration": f"TDS on {invoice['invoice_number']}"
        })

    if entries:
        voucher_number = await get_next_voucher_number(session, "purchase", branch_id)

        voucher = Voucher(
            id=str(uuid.uuid4()),
            voucher_type="purchase",
            voucher_number=voucher_number,
            voucher_date=invoice["invoice_date"],
            branch_id=branch_id,
            entries=entries,
            narration=f"Purchase Invoice {invoice['invoice_number']} - {invoice['supplier_name']}",
            reference_type="purchase_invoice",
            reference_id=invoice["id"],
            total_debit=sum(e["debit"] for e in entries),
            total_credit=sum(e["credit"] for e in entries),
            status="approved",
            created_by=username,
            created_at=datetime.now(timezone.utc)
        )
        session.add(voucher)
        await session.flush()

        inv_res = await session.execute(select(PurchaseInvoice).where(PurchaseInvoice.id == invoice["id"]))
        inv = inv_res.scalar_one_or_none()
        if inv: inv.voucher_id = voucher.id

        await post_to_ledgers(session, voucher.id, voucher_number, "purchase",
            invoice["invoice_date"], branch_id, entries
        )


# ==================== PURCHASE RETURNS ====================

@router.get("/returns")
async def get_purchase_returns(
    branch_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get purchase returns"""
    query = select(PurchaseReturn)
    if branch_id:
        query = query.where(PurchaseReturn.branch_id == branch_id)
    if start_date:
        query = query.where(PurchaseReturn.return_date >= start_date)
    if end_date:
        query = query.where(PurchaseReturn.return_date <= end_date)

    query = query.order_by(desc(PurchaseReturn.return_date))
    result = await session.execute(query)
    returns = result.scalars().all()
    return [to_dict(r) for r in returns]


@router.post("/returns")
async def create_purchase_return(return_data: dict, session: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Create purchase return (debit note)"""

    # Validate original invoice
    res = await session.execute(select(PurchaseInvoice).where(PurchaseInvoice.id == return_data["purchase_invoice_id"]))
    invoice = res.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Original invoice not found")

    return_number = await get_next_document_number(session, "PRN", PurchaseReturn)

    # Consume stock (return to supplier)
    for item in return_data.get("items", []):
        result = await consume_stock_fifo(
            session, item["item_id"], return_data["branch_id"],
            item["godown_id"], item["quantity"],
            "purchase_return", return_number, return_number,
            return_data["return_date"]
        )

        if not result["success"]:
            raise HTTPException(
                status_code=400,
                detail=f"Stock error for {item['item_name']}: {result['error']}"
            )

    new_return = PurchaseReturn(
        id=str(uuid.uuid4()),
        **return_data,
        return_number=return_number,
        status="completed",
        created_by=current_user["username"],
        created_at=datetime.now(timezone.utc)
    )

    session.add(new_return)
    await session.flush()

    # Create debit note accounting entry
    await create_debit_note_entry(session, to_dict(new_return), to_dict(invoice), current_user["username"])

    await session.commit()
    return to_dict(new_return)


async def create_debit_note_entry(session: AsyncSession, return_doc: dict, original_invoice: dict, username: str):
    """Create accounting entry for purchase return (debit note)"""

    branch_id = return_doc["branch_id"]

    async def find_ledger(name):
        res = await session.execute(select(Ledger).where(Ledger.name == name, Ledger.branch_id == branch_id))
        return res.scalar_one_or_none()

    supplier_ledger = await find_ledger(return_doc["supplier_name"])
    purchase_ledger = await find_ledger("Purchase Account")
    cgst_input = await find_ledger("CGST Input")
    sgst_input = await find_ledger("SGST Input")
    igst_input = await find_ledger("IGST Input")

    entries = []

    # Debit: Supplier
    if supplier_ledger:
        entries.append({
            "ledger_id": supplier_ledger.id,
            "ledger_name": supplier_ledger.name,
            "debit": return_doc["grand_total"],
            "credit": 0,
            "narration": f"Purchase Return {return_doc['return_number']}"
        })

    # Credit: Purchase
    if purchase_ledger:
        entries.append({
            "ledger_id": purchase_ledger.id,
            "ledger_name": purchase_ledger.name,
            "debit": 0,
            "credit": return_doc["taxable_amount"],
            "narration": f"Purchase Return {return_doc['return_number']}"
        })

    # Credit: GST (reversal)
    if return_doc.get("cgst_amount", 0) > 0 and cgst_input:
        entries.append({
            "ledger_id": cgst_input.id,
            "ledger_name": cgst_input.name,
            "debit": 0,
            "credit": return_doc["cgst_amount"],
            "narration": f"CGST reversal on {return_doc['return_number']}"
        })

    if return_doc.get("sgst_amount", 0) > 0 and sgst_input:
        entries.append({
            "ledger_id": sgst_input.id,
            "ledger_name": sgst_input.name,
            "debit": 0,
            "credit": return_doc["sgst_amount"],
            "narration": f"SGST reversal on {return_doc['return_number']}"
        })

    if return_doc.get("igst_amount", 0) > 0 and igst_input:
        entries.append({
            "ledger_id": igst_input.id,
            "ledger_name": igst_input.name,
            "debit": 0,
            "credit": return_doc["igst_amount"],
            "narration": f"IGST reversal on {return_doc['return_number']}"
        })

    if entries:
        voucher_number = await get_next_voucher_number(session, "debit_note", branch_id)

        voucher = Voucher(
            id=str(uuid.uuid4()),
            voucher_type="debit_note",
            voucher_number=voucher_number,
            voucher_date=return_doc["return_date"],
            branch_id=branch_id,
            entries=entries,
            narration=f"Debit Note {return_doc['return_number']} against {original_invoice['invoice_number']}",
            reference_type="purchase_return",
            reference_id=return_doc["id"],
            total_debit=sum(e["debit"] for e in entries),
            total_credit=sum(e["credit"] for e in entries),
            status="approved",
            created_by=username,
            created_at=datetime.now(timezone.utc)
        )
        session.add(voucher)

        await post_to_ledgers(session, voucher.id, voucher_number, "debit_note",
            return_doc["return_date"], branch_id, entries
        )
