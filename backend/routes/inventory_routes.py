"""
HOOREN ERP - Inventory Routes
Items, Stock, Batches, Transfers, Adjustments
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime, timezone
import uuid

router = APIRouter(prefix="/api/inventory", tags=["inventory"])

from server import db
from utils import get_current_user
from services.inventory_service import (
    create_stock_batch,
    consume_stock_fifo,
    get_stock_summary,
    get_stock_ledger,
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
    current_user: dict = Depends(get_current_user)
):
    """Get all items with filters"""
    query = {}
    if is_active is not None:
        query["is_active"] = is_active
    if category:
        query["category"] = category
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"code": {"$regex": search, "$options": "i"}}
        ]
    
    items = await db.items.find(query, {"_id": 0}).to_list(10000)
    return items


@router.get("/items/{item_id}")
async def get_item(item_id: str, current_user: dict = Depends(get_current_user)):
    """Get item details"""
    item = await db.items.find_one({"id": item_id}, {"_id": 0})
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.post("/items")
async def create_item(item_data: dict, current_user: dict = Depends(get_current_user)):
    """Create a new item"""
    # Check code uniqueness
    existing = await db.items.find_one({"code": item_data["code"]})
    if existing:
        raise HTTPException(status_code=400, detail="Item code already exists")
    
    item_doc = {
        "id": str(uuid.uuid4()),
        **item_data,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.items.insert_one(item_doc)
    item_doc.pop("_id", None)
    return item_doc


@router.put("/items/{item_id}")
async def update_item(
    item_id: str,
    item_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Update item"""
    existing = await db.items.find_one({"id": item_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Check code uniqueness
    if "code" in item_data:
        code_exists = await db.items.find_one({
            "code": item_data["code"],
            "id": {"$ne": item_id}
        })
        if code_exists:
            raise HTTPException(status_code=400, detail="Item code already exists")
    
    item_data["modified_at"] = datetime.now(timezone.utc).isoformat()
    await db.items.update_one({"id": item_id}, {"$set": item_data})
    
    return {"message": "Item updated"}


@router.delete("/items/{item_id}")
async def delete_item(item_id: str, current_user: dict = Depends(get_current_user)):
    """Soft delete item"""
    existing = await db.items.find_one({"id": item_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Check for stock
    stock = await db.stock_batches.count_documents({
        "item_id": item_id,
        "remaining_quantity": {"$gt": 0}
    })
    if stock > 0:
        raise HTTPException(status_code=400, detail="Cannot delete item with stock")
    
    await db.items.update_one({"id": item_id}, {"$set": {"is_active": False}})
    return {"message": "Item deleted"}


@router.get("/categories")
async def get_categories(current_user: dict = Depends(get_current_user)):
    """Get distinct item categories"""
    categories = await db.items.distinct("category")
    return categories


# ==================== STOCK ====================

@router.get("/stock")
async def get_stock(
    item_id: Optional[str] = None,
    branch_id: Optional[str] = None,
    godown_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get stock summary"""
    result = await get_stock_summary(db, item_id, branch_id, godown_id)
    return result


@router.get("/stock/batches")
async def get_batches(
    item_id: Optional[str] = None,
    branch_id: Optional[str] = None,
    godown_id: Optional[str] = None,
    has_stock: bool = True,
    current_user: dict = Depends(get_current_user)
):
    """Get stock batches"""
    query = {"is_active": True}
    if item_id:
        query["item_id"] = item_id
    if branch_id:
        query["branch_id"] = branch_id
    if godown_id:
        query["godown_id"] = godown_id
    if has_stock:
        query["remaining_quantity"] = {"$gt": 0}
    
    batches = await db.stock_batches.find(query, {"_id": 0}).sort("purchase_date", 1).to_list(10000)
    
    # Enrich with item info
    for batch in batches:
        item = await db.items.find_one({"id": batch["item_id"]}, {"_id": 0})
        batch["item_name"] = item["name"] if item else "Unknown"
        batch["item_code"] = item["code"] if item else ""
    
    return batches


@router.get("/stock/batches/{batch_id}")
async def get_batch(batch_id: str, current_user: dict = Depends(get_current_user)):
    """Get batch details"""
    batch = await db.stock_batches.find_one({"id": batch_id}, {"_id": 0})
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    return batch


@router.get("/stock/ledger/{item_id}")
async def get_item_stock_ledger(
    item_id: str,
    branch_id: Optional[str] = None,
    godown_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get stock ledger for an item"""
    result = await get_stock_ledger(db, item_id, branch_id, godown_id, start_date, end_date)
    return result


@router.get("/stock/expiring")
async def get_expiring_stock(
    days: int = 30,
    branch_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get stock expiring within N days"""
    from datetime import timedelta
    
    cutoff_date = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()[:10]
    
    query = {
        "remaining_quantity": {"$gt": 0},
        "expiry_date": {"$lte": cutoff_date, "$ne": None},
        "is_active": True
    }
    if branch_id:
        query["branch_id"] = branch_id
    
    batches = await db.stock_batches.find(query, {"_id": 0}).sort("expiry_date", 1).to_list(1000)
    
    # Enrich
    for batch in batches:
        item = await db.items.find_one({"id": batch["item_id"]}, {"_id": 0})
        batch["item_name"] = item["name"] if item else "Unknown"
    
    return batches


# ==================== STOCK ADJUSTMENT ====================

@router.post("/stock/adjustment")
async def create_stock_adjustment(
    adjustment_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Create stock adjustment"""
    result = await process_stock_adjustment(db, adjustment_data, current_user["username"])
    return result


@router.get("/stock/adjustments")
async def get_adjustments(
    branch_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get stock adjustments"""
    query = {}
    if branch_id:
        query["branch_id"] = branch_id
    
    date_query = {}
    if start_date:
        date_query["$gte"] = start_date
    if end_date:
        date_query["$lte"] = end_date
    if date_query:
        query["adjustment_date"] = date_query
    
    adjustments = await db.stock_adjustments.find(query, {"_id": 0}).sort("adjustment_date", -1).to_list(1000)
    return adjustments


# ==================== INTER-BRANCH TRANSFER ====================

@router.post("/stock/transfer")
async def create_inter_branch_transfer(
    transfer_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Create inter-branch stock transfer"""
    result = await process_inter_branch_transfer(db, transfer_data, current_user["username"])
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Transfer failed"))
    
    return result["transfer"]


@router.get("/stock/transfers")
async def get_transfers(
    from_branch_id: Optional[str] = None,
    to_branch_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get inter-branch transfers"""
    query = {}
    if from_branch_id:
        query["from_branch_id"] = from_branch_id
    if to_branch_id:
        query["to_branch_id"] = to_branch_id
    
    date_query = {}
    if start_date:
        date_query["$gte"] = start_date
    if end_date:
        date_query["$lte"] = end_date
    if date_query:
        query["transfer_date"] = date_query
    
    transfers = await db.inter_branch_transfers.find(query, {"_id": 0}).sort("transfer_date", -1).to_list(1000)
    
    # Enrich with branch names
    for transfer in transfers:
        from_branch = await db.branches.find_one({"id": transfer["from_branch_id"]})
        to_branch = await db.branches.find_one({"id": transfer["to_branch_id"]})
        transfer["from_branch_name"] = from_branch["name"] if from_branch else "Unknown"
        transfer["to_branch_name"] = to_branch["name"] if to_branch else "Unknown"
    
    return transfers


# ==================== REPORTS ====================

@router.get("/reports/stock-valuation")
async def get_stock_valuation(
    branch_id: Optional[str] = None,
    godown_id: Optional[str] = None,
    category: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get stock valuation report"""
    stock_summary = await get_stock_summary(db, None, branch_id, godown_id)
    
    # Filter by category if specified
    if category:
        filtered = []
        for item in stock_summary:
            item_doc = await db.items.find_one({"id": item["item_id"]})
            if item_doc and item_doc.get("category") == category:
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
    current_user: dict = Depends(get_current_user)
):
    """Get item movement report"""
    query = {
        "item_id": item_id,
        "transaction_date": {"$gte": start_date, "$lte": end_date}
    }
    if branch_id:
        query["branch_id"] = branch_id
    
    transactions = await db.stock_transactions.find(query, {"_id": 0}).sort("transaction_date", 1).to_list(10000)
    
    # Calculate totals
    total_in = sum(t["quantity"] for t in transactions if t["quantity"] > 0)
    total_out = sum(abs(t["quantity"]) for t in transactions if t["quantity"] < 0)
    
    item = await db.items.find_one({"id": item_id}, {"_id": 0})
    
    return {
        "item_id": item_id,
        "item_name": item["name"] if item else "Unknown",
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
    current_user: dict = Depends(get_current_user)
):
    """Get item profitability report"""
    result = await get_item_profitability(db, item_id, branch_id, start_date, end_date)
    
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
