"""
HOOREN ERP - Inventory Routes
Items, Stock, Batches, Transfers, Adjustments
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime, timezone
import uuid
import json

router = APIRouter(prefix="/api/inventory", tags=["inventory"])

from utils import get_current_user
from database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, desc
from db_models import Item as DBItem, StockBatch as DBStockBatch, Branch as DBBranch, Godown as DBGodown, StockAdjustment as DBStockAdjustment, InterBranchTransfer as DBInterBranchTransfer, ManualStockOutward as DBManualStockOutward, StockTransaction as DBStockTransaction

def to_dict(obj):
    if not obj: return {}
    d = {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
    for k, v in d.items():
        if isinstance(v, datetime):
            d[k] = v.isoformat()
    return d

from services.inventory_service import (
    create_stock_batch,
    consume_stock_fifo,
    create_stock_transaction,
    get_stock_summary,
    get_stock_ledger,
    get_stock_movements,
    get_ready_stock_summary,
    process_stock_adjustment,
    process_inter_branch_transfer,
    get_next_batch_number,
    get_item_profitability
)


# ==================== ITEMS ====================

@router.get("/items")
async def get_items(
    category: Optional[str] = None,
    search: Optional[str] = None,
    is_active: bool = True,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Get all items with filters"""
    query = select(DBItem)
    if is_active is not None:
        query = query.where(DBItem.is_active == is_active)
    if category:
        query = query.where(DBItem.category == category)
    if search:
        query = query.where((DBItem.name.ilike(f"%{search}%")) | (DBItem.code.ilike(f"%{search}%")))
    
    res = await session.execute(query)
    return [to_dict(i) for i in res.scalars().all()]


@router.get("/items/{item_id}")
async def get_item(item_id: str, current_user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    """Get item details"""
    res = await session.execute(select(DBItem).where(DBItem.id == item_id))
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return to_dict(item)


@router.post("/items")
async def create_item(item_data: dict, current_user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    """Create a new item"""
    # Check code uniqueness
    res = await session.execute(select(DBItem).where(DBItem.code == item_data["code"]))
    existing = res.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Item code already exists")
    
    new_item = DBItem(id=str(uuid.uuid4()), **item_data, is_active=True, created_at=datetime.now(timezone.utc))
    session.add(new_item)
    await session.commit()
    return to_dict(new_item)


@router.put("/items/{item_id}")
async def update_item(
    item_id: str,
    item_data: dict,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Update item"""
    res = await session.execute(select(DBItem).where(DBItem.id == item_id))
    existing = res.scalar_one_or_none()
    if not existing:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Check code uniqueness
    if "code" in item_data:
        code_res = await session.execute(select(DBItem).where(DBItem.code == item_data["code"]).where(DBItem.id != item_id))
        code_exists = code_res.scalar_one_or_none()
        if code_exists:
            raise HTTPException(status_code=400, detail="Item code already exists")
    
    skip_fields = {"id", "created_at", "modified_at", "is_active"}
    for key, value in item_data.items():
        if key not in skip_fields:
            setattr(existing, key, value)

    existing.modified_at = datetime.now(timezone.utc)
    await session.commit()

    return {"message": "Item updated"}


@router.delete("/items/{item_id}")
async def delete_item(item_id: str, current_user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    """Soft delete item"""
    res = await session.execute(select(DBItem).where(DBItem.id == item_id))
    existing = res.scalar_one_or_none()
    if not existing:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Check for stock
    stock_res = await session.execute(select(func.count(DBStockBatch.id)).where(DBStockBatch.item_id == item_id).where(DBStockBatch.remaining_quantity > 0))
    stock_count = stock_res.scalar() or 0
    if stock_count > 0:
        raise HTTPException(status_code=400, detail="Cannot delete item with stock")
    
    existing.is_active = False
    await session.commit()
    return {"message": "Item deleted"}


@router.get("/categories")
async def get_categories(current_user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    """Get distinct item categories"""
    res = await session.execute(select(DBItem.category).distinct())
    categories = res.scalars().all()
    return [c for c in categories if c]


# ==================== STOCK ====================

@router.get("/stock")
async def get_stock(
    item_id: Optional[str] = None,
    branch_id: Optional[str] = None,
    godown_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Get stock summary"""
    result = await get_stock_summary(session, item_id, branch_id, godown_id)
    return result


@router.get("/ready-stock")
async def get_ready_stock(
    branch_id: Optional[str] = None,
    godown_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Get simplified ready stock grouped by item."""
    return await get_ready_stock_summary(session, branch_id, godown_id)


@router.get("/stock/batches")
async def get_batches(
    item_id: Optional[str] = None,
    branch_id: Optional[str] = None,
    godown_id: Optional[str] = None,
    has_stock: bool = True,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Get stock batches"""
    query = select(DBStockBatch).where(DBStockBatch.is_active == True)
    if item_id:
        query = query.where(DBStockBatch.item_id == item_id)
    if branch_id:
        query = query.where(DBStockBatch.branch_id == branch_id)
    if godown_id:
        query = query.where(DBStockBatch.godown_id == godown_id)
    if has_stock:
        query = query.where(DBStockBatch.remaining_quantity > 0)
    
    query = query.order_by(DBStockBatch.purchase_date)
    res = await session.execute(query)
    batches = res.scalars().all()
    
    result = []
    for batch in batches:
        b_dict = to_dict(batch)
        item_res = await session.execute(select(DBItem).where(DBItem.id == batch.item_id))
        item = item_res.scalar_one_or_none()
        b_dict["item_name"] = item.name if item else "Unknown"
        b_dict["item_code"] = item.code if item else ""
        result.append(b_dict)
    
    return result


@router.get("/stock/batches/{batch_id}")
async def get_batch(batch_id: str, current_user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    """Get batch details"""
    res = await session.execute(select(DBStockBatch).where(DBStockBatch.id == batch_id))
    batch = res.scalar_one_or_none()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    return to_dict(batch)


@router.get("/stock/ledger/{item_id}")
async def get_item_stock_ledger(
    item_id: str,
    branch_id: Optional[str] = None,
    godown_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Get stock ledger for an item"""
    result = await get_stock_ledger(session, item_id, branch_id, godown_id, start_date, end_date)
    return result


@router.get("/stock/movements")
async def get_inventory_movements(
    branch_id: Optional[str] = None,
    godown_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Get simplified inventory inward/outward movements."""
    return await get_stock_movements(session, branch_id, godown_id, start_date, end_date)


@router.post("/stock/outward")
async def create_manual_stock_outward(
    outward_data: dict,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Create a manual inventory out entry."""
    required_fields = ["branch_id", "godown_id", "item_id", "quantity", "transaction_date"]
    missing = [field for field in required_fields if not outward_data.get(field)]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing fields: {', '.join(missing)}")

    quantity = float(outward_data.get("quantity") or 0)
    if quantity <= 0:
        raise HTTPException(status_code=400, detail="Out Qty must be greater than zero")

    item_res = await session.execute(select(DBItem).where(DBItem.id == outward_data["item_id"]))
    item = item_res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    ref_id = str(uuid.uuid4())
    ref_number = f"OUT/{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    result = await consume_stock_fifo(
        session,
        outward_data["item_id"],
        outward_data["branch_id"],
        outward_data["godown_id"],
        quantity,
        "manual_out",
        ref_id,
        ref_number,
        outward_data["transaction_date"]
    )

    if not result.get("success"):
        transaction_doc = await create_stock_transaction(
            session,
            outward_data["item_id"],
            outward_data["branch_id"],
            outward_data["godown_id"],
            "manual_out",
            -quantity,
            0,
            0,
            None,
            None,
            "manual_out",
            ref_id,
            ref_number,
            outward_data["transaction_date"],
            narration=outward_data.get("remarks") or "Manual stock out"
        )
        result = {
            "success": True,
            "manual_negative_stock": True,
            "error": result.get("error"),
            "transaction_id": transaction_doc["id"]
        }

    new_outward = DBManualStockOutward(
        id=ref_id,
        outward_number=ref_number,
        branch_id=outward_data["branch_id"],
        godown_id=outward_data["godown_id"],
        item_id=outward_data["item_id"],
        item_name=item.name,
        quantity=quantity,
        transaction_date=outward_data["transaction_date"],
        remarks=outward_data.get("remarks", ""),
        created_by=current_user["username"],
        stock_result=json.dumps(result),
        created_at=datetime.now(timezone.utc)
    )
    session.add(new_outward)
    await session.commit()
    return to_dict(new_outward)


@router.get("/stock/outwards")
async def get_manual_stock_outwards(
    branch_id: Optional[str] = None,
    godown_id: Optional[str] = None,
    item_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Get manual inventory out history."""
    query = select(DBManualStockOutward)
    if branch_id:
        query = query.where(DBManualStockOutward.branch_id == branch_id)
    if godown_id:
        query = query.where(DBManualStockOutward.godown_id == godown_id)
    if item_id:
        query = query.where(DBManualStockOutward.item_id == item_id)

    if start_date:
        query = query.where(DBManualStockOutward.transaction_date >= start_date)
    if end_date:
        query = query.where(DBManualStockOutward.transaction_date <= end_date)

    query = query.order_by(desc(DBManualStockOutward.transaction_date), desc(DBManualStockOutward.created_at))
    res = await session.execute(query)
    outwards = [to_dict(o) for o in res.scalars().all()]

    for outward in outwards:
        br_res = await session.execute(select(DBBranch).where(DBBranch.id == outward.get("branch_id")))
        gd_res = await session.execute(select(DBGodown).where(DBGodown.id == outward.get("godown_id")))
        it_res = await session.execute(select(DBItem).where(DBItem.id == outward.get("item_id")))
        
        branch = br_res.scalar_one_or_none()
        godown = gd_res.scalar_one_or_none()
        item = it_res.scalar_one_or_none()

        outward["branch_name"] = branch.name if branch else ""
        outward["godown_name"] = godown.name if godown else ""
        outward["item_code"] = item.code if item else ""
        outward["item_name"] = item.name if item else outward.get("item_name", "")
        outward["size"] = (
            getattr(item, "print_name", None)
            or getattr(item, "alternate_unit", None)
            or getattr(item, "unit", "")
            or ""
        ) if item else ""

    return outwards


@router.get("/stock/expiring")
async def get_expiring_stock(
    days: int = 30,
    branch_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Get stock expiring within N days"""
    from datetime import timedelta
    
    cutoff_date = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()[:10]
    
    query = select(DBStockBatch).where(DBStockBatch.remaining_quantity > 0).where(DBStockBatch.is_active == True).where(DBStockBatch.expiry_date <= cutoff_date).where(DBStockBatch.expiry_date != None)
    if branch_id:
        query = query.where(DBStockBatch.branch_id == branch_id)
    
    query = query.order_by(DBStockBatch.expiry_date)
    res = await session.execute(query)
    batches = res.scalars().all()
    
    # Enrich
    result = []
    for batch in batches:
        b_dict = to_dict(batch)
        item_res = await session.execute(select(DBItem).where(DBItem.id == batch.item_id))
        item = item_res.scalar_one_or_none()
        b_dict["item_name"] = item.name if item else "Unknown"
        result.append(b_dict)
    
    return result


# ==================== STOCK ADJUSTMENT ====================

@router.post("/stock/adjustment")
async def create_stock_adjustment(
    adjustment_data: dict,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Create stock adjustment"""
    result = await process_stock_adjustment(session, adjustment_data, current_user["username"])
    return result


@router.get("/stock/adjustments")
async def get_adjustments(
    branch_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Get stock adjustments"""
    query = select(DBStockAdjustment)
    if branch_id:
        query = query.where(DBStockAdjustment.branch_id == branch_id)
    
    if start_date:
        query = query.where(DBStockAdjustment.adjustment_date >= start_date)
    if end_date:
        query = query.where(DBStockAdjustment.adjustment_date <= end_date)
    
    query = query.order_by(desc(DBStockAdjustment.adjustment_date))
    res = await session.execute(query)
    adjustments = [to_dict(a) for a in res.scalars().all()]
    
    for adjustment in adjustments:
        gd_res = await session.execute(select(DBGodown).where(DBGodown.id == adjustment.get("godown_id")))
        br_res = await session.execute(select(DBBranch).where(DBBranch.id == adjustment.get("branch_id")))
        godown = gd_res.scalar_one_or_none()
        branch = br_res.scalar_one_or_none()
        
        adjustment["godown_name"] = godown.name if godown else ""
        adjustment["branch_name"] = branch.name if branch else ""
        try:
            items = json.loads(adjustment.get("items", "[]"))
            adjustment["item_count"] = len(items)
        except:
            adjustment["item_count"] = 0

    return adjustments


# ==================== INTER-BRANCH TRANSFER ====================

@router.post("/stock/transfer")
async def create_inter_branch_transfer(
    transfer_data: dict,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Create inter-branch stock transfer"""
    result = await process_inter_branch_transfer(session, transfer_data, current_user["username"])
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Transfer failed"))
    
    return result["transfer"]


@router.get("/stock/transfers")
async def get_transfers(
    from_branch_id: Optional[str] = None,
    to_branch_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Get inter-branch transfers"""
    query = select(DBInterBranchTransfer)
    if from_branch_id:
        query = query.where(DBInterBranchTransfer.from_branch_id == from_branch_id)
    if to_branch_id:
        query = query.where(DBInterBranchTransfer.to_branch_id == to_branch_id)
    if start_date:
        query = query.where(DBInterBranchTransfer.transfer_date >= start_date)
    if end_date:
        query = query.where(DBInterBranchTransfer.transfer_date <= end_date)

    query = query.order_by(desc(DBInterBranchTransfer.transfer_date))
    res = await session.execute(query)
    transfers = [to_dict(t) for t in res.scalars().all()]
    
    # Enrich with branch names
    for transfer in transfers:
        from_res = await session.execute(select(DBBranch).where(DBBranch.id == transfer["from_branch_id"]))
        to_res = await session.execute(select(DBBranch).where(DBBranch.id == transfer["to_branch_id"]))
        from_branch = from_res.scalar_one_or_none()
        to_branch = to_res.scalar_one_or_none()
        transfer["from_branch_name"] = from_branch.name if from_branch else "Unknown"
        transfer["to_branch_name"] = to_branch.name if to_branch else "Unknown"
    
    return transfers


# ==================== REPORTS ====================

@router.get("/reports/stock-valuation")
async def get_stock_valuation(
    branch_id: Optional[str] = None,
    godown_id: Optional[str] = None,
    category: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Get stock valuation report"""
    stock_summary = await get_stock_summary(session, None, branch_id, godown_id)
    
    # Filter by category if specified
    if category:
        filtered = []
        for item in stock_summary:
            item_res = await session.execute(select(DBItem).where(DBItem.id == item["item_id"]))
            item_doc = item_res.scalar_one_or_none()
            if item_doc and item_doc.category == category:
                filtered.append(item)
        stock_summary = filtered
    
    total_value = sum(s["total_value"] for s in stock_summary)
    total_quantity = sum(s["total_quantity"] for s in stock_summary)
    
    return {
        "items": stock_summary,
        "total_items": len(stock_summary),
        "total_quantity": total_quantity,
        "total_value": round(total_value, 2)
    }


@router.get("/reports/item-movement")
async def get_item_movement(
    item_id: str,
    start_date: str,
    end_date: str,
    branch_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Get item movement report"""
    query = select(DBStockTransaction).where(
        DBStockTransaction.item_id == item_id,
        DBStockTransaction.transaction_date >= start_date,
        DBStockTransaction.transaction_date <= end_date,
    )
    if branch_id:
        query = query.where(DBStockTransaction.branch_id == branch_id)

    query = query.order_by(DBStockTransaction.transaction_date)
    res = await session.execute(query)
    transactions = [to_dict(t) for t in res.scalars().all()]
    
    # Calculate totals
    total_in = sum(t["quantity"] for t in transactions if t["quantity"] > 0)
    total_out = sum(abs(t["quantity"]) for t in transactions if t["quantity"] < 0)
    
    item_res = await session.execute(select(DBItem).where(DBItem.id == item_id))
    item = item_res.scalar_one_or_none()
    
    return {
        "item_id": item_id,
        "item_name": item.name if item else "Unknown",
        "period": {"start_date": start_date, "end_date": end_date},
        "transactions": transactions,
        "total_in": total_in,
        "total_out": total_out,
        "net_movement": total_in - total_out
    }


@router.get("/reports/profitability")
async def get_profitability_report(
    item_id: Optional[str] = None,
    branch_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Get item profitability report"""
    result = await get_item_profitability(session, item_id, branch_id, start_date, end_date)
    
    total_sales = sum(r["sales_value"] for r in result)
    total_cost = sum(r["cost_value"] for r in result)
    total_profit = sum(r["profit"] for r in result)
    
    return {
        "items": result,
        "summary": {
            "total_sales": round(total_sales, 2),
            "total_cost": round(total_cost, 2),
            "total_profit": round(total_profit, 2),
            "margin_percent": round((total_profit / total_sales * 100) if total_sales > 0 else 0, 2)
        }
    }
