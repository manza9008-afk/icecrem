"""
HOOREN ERP - Inventory Services
FIFO valuation, batch tracking, stock management
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import uuid

DatabaseHandle = Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from db_models import Branch as DBBranch
from db_models import Godown as DBGodown
from db_models import InterBranchTransfer as DBInterBranchTransfer
from db_models import Item as DBItem
from db_models import StockAdjustment as DBStockAdjustment
from db_models import StockBatch as DBStockBatch
from db_models import StockTransaction as DBStockTransaction


def _is_sql_session(db: Any) -> bool:
    return isinstance(db, AsyncSession)


def _to_dict(obj):
    if not obj:
        return {}
    data = {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
    for key, value in data.items():
        if isinstance(value, datetime):
            data[key] = value.isoformat()
    return data


async def get_next_batch_number(
    db: DatabaseHandle,
    item_id: str,
    branch_id: str
) -> str:
    """Generate next batch number for item"""
    if _is_sql_session(db):
        result = await db.execute(
            select(DBStockBatch)
            .where(DBStockBatch.item_id == item_id, DBStockBatch.branch_id == branch_id)
            .order_by(desc(DBStockBatch.created_at))
            .limit(1)
        )
        last_batch = result.scalar_one_or_none()
        if last_batch:
            try:
                new_num = int(last_batch.batch_number.split("-")[-1]) + 1
            except (ValueError, IndexError, AttributeError):
                new_num = 1
        else:
            new_num = 1

        item_res = await db.execute(select(DBItem).where(DBItem.id == item_id))
        item = item_res.scalar_one_or_none()
        item_code = item.code if item else "ITEM"
        return f"{item_code}-{new_num:04d}"
    
    # Get last batch for this item
    last_batch = await db.stock_batches.find_one(
        {"item_id": item_id, "branch_id": branch_id},
        sort=[("created_at", -1)]
    )
    
    if last_batch:
        try:
            parts = last_batch["batch_number"].split("-")
            last_num = int(parts[-1])
            new_num = last_num + 1
        except:
            new_num = 1
    else:
        new_num = 1
    
    # Get item code
    item = await db.items.find_one({"id": item_id})
    item_code = item["code"] if item else "ITEM"
    
    return f"{item_code}-{new_num:04d}"


async def create_stock_batch(
    db: DatabaseHandle,
    item_id: str,
    branch_id: str,
    godown_id: str,
    batch_number: str,
    quantity: float,
    unit_cost: float,
    purchase_date: str,
    expiry_date: Optional[str],
    mfg_date: Optional[str],
    supplier_id: Optional[str],
    reference_type: str,
    reference_id: str,
    reference_number: str
) -> Dict[str, Any]:
    """Create a new stock batch"""
    if _is_sql_session(db):
        batch_doc = {
            "id": str(uuid.uuid4()),
            "item_id": item_id,
            "branch_id": branch_id,
            "godown_id": godown_id,
            "batch_number": batch_number,
            "quantity": quantity,
            "remaining_quantity": quantity,
            "unit_cost": unit_cost,
            "purchase_date": purchase_date,
            "expiry_date": expiry_date,
            "mfg_date": mfg_date,
            "supplier_id": supplier_id,
            "reference_type": reference_type,
            "reference_id": reference_id,
            "reference_number": reference_number,
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
        }
        db.add(DBStockBatch(**batch_doc))
        await db.flush()

        transaction_type = {
            "purchase_invoice": "purchase",
            "transfer": "transfer_in",
            "adjustment": "adjustment_in",
        }.get(reference_type, reference_type)
        await create_stock_transaction(
            db, item_id, branch_id, godown_id, transaction_type, quantity, unit_cost,
            quantity * unit_cost, batch_doc["id"], batch_number, reference_type,
            reference_id, reference_number, purchase_date,
            narration=f"Stock inward via {reference_type.replace('_', ' ')}",
        )
        batch_doc["created_at"] = batch_doc["created_at"].isoformat()
        return batch_doc
    
    batch_doc = {
        "id": str(uuid.uuid4()),
        "item_id": item_id,
        "branch_id": branch_id,
        "godown_id": godown_id,
        "batch_number": batch_number,
        "quantity": quantity,
        "remaining_quantity": quantity,
        "unit_cost": unit_cost,
        "purchase_date": purchase_date,
        "expiry_date": expiry_date,
        "mfg_date": mfg_date,
        "supplier_id": supplier_id,
        "reference_type": reference_type,
        "reference_id": reference_id,
        "reference_number": reference_number,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.stock_batches.insert_one(batch_doc)

    transaction_type = {
        "purchase_invoice": "purchase",
        "transfer": "transfer_in",
        "adjustment": "adjustment_in",
    }.get(reference_type, reference_type)

    await create_stock_transaction(
        db,
        item_id,
        branch_id,
        godown_id,
        transaction_type,
        quantity,
        unit_cost,
        quantity * unit_cost,
        batch_doc["id"],
        batch_number,
        reference_type,
        reference_id,
        reference_number,
        purchase_date,
        narration=f"Stock inward via {reference_type.replace('_', ' ')}"
    )

    return batch_doc


async def consume_stock_fifo(
    db: DatabaseHandle,
    item_id: str,
    branch_id: str,
    godown_id: str,
    quantity: float,
    reference_type: str,
    reference_id: str,
    reference_number: str,
    transaction_date: str
) -> Dict[str, Any]:
    """Consume stock using FIFO method"""
    if _is_sql_session(db):
        consumed_batches = []
        remaining_qty = quantity
        total_cost = 0.0

        result = await db.execute(
            select(DBStockBatch)
            .where(
                DBStockBatch.item_id == item_id,
                DBStockBatch.branch_id == branch_id,
                DBStockBatch.godown_id == godown_id,
                DBStockBatch.remaining_quantity > 0,
                DBStockBatch.is_active == True,
            )
            .order_by(DBStockBatch.purchase_date)
        )
        batches = result.scalars().all()

        for batch in batches:
            if remaining_qty <= 0:
                break
            available = batch.remaining_quantity or 0
            consume_qty = min(available, remaining_qty)
            batch.remaining_quantity = available - consume_qty

            batch_cost = consume_qty * (batch.unit_cost or 0)
            total_cost += batch_cost
            consumed_batches.append({
                "batch_id": batch.id,
                "batch_number": batch.batch_number,
                "quantity": consume_qty,
                "unit_cost": batch.unit_cost or 0,
                "total_cost": batch_cost,
            })

            await create_stock_transaction(
                db, item_id, branch_id, godown_id, "sale", -consume_qty,
                batch.unit_cost or 0, -batch_cost, batch.id, batch.batch_number,
                reference_type, reference_id, reference_number, transaction_date,
            )
            remaining_qty -= consume_qty

        if remaining_qty > 0:
            return {"success": False, "error": f"Insufficient stock. Short by {remaining_qty}", "consumed_batches": consumed_batches}

        avg_cost = total_cost / quantity if quantity > 0 else 0
        return {
            "success": True,
            "consumed_batches": consumed_batches,
            "total_quantity": quantity,
            "total_cost": total_cost,
            "average_cost": avg_cost,
        }
    
    consumed_batches = []
    remaining_qty = quantity
    total_cost = 0.0
    
    # Get available batches ordered by purchase date (FIFO)
    batches = await db.stock_batches.find({
        "item_id": item_id,
        "branch_id": branch_id,
        "godown_id": godown_id,
        "remaining_quantity": {"$gt": 0},
        "is_active": True
    }).sort("purchase_date", 1).to_list(1000)
    
    for batch in batches:
        if remaining_qty <= 0:
            break
        
        available = batch["remaining_quantity"]
        consume_qty = min(available, remaining_qty)
        
        # Update batch
        new_remaining = available - consume_qty
        await db.stock_batches.update_one(
            {"id": batch["id"]},
            {"$set": {"remaining_quantity": new_remaining}}
        )
        
        batch_cost = consume_qty * batch["unit_cost"]
        total_cost += batch_cost
        
        consumed_batches.append({
            "batch_id": batch["id"],
            "batch_number": batch["batch_number"],
            "quantity": consume_qty,
            "unit_cost": batch["unit_cost"],
            "total_cost": batch_cost
        })
        
        # Create stock transaction
        await create_stock_transaction(
            db, item_id, branch_id, godown_id,
            "sale", -consume_qty, batch["unit_cost"], -batch_cost,
            batch["id"], batch["batch_number"],
            reference_type, reference_id, reference_number, transaction_date
        )
        
        remaining_qty -= consume_qty
    
    if remaining_qty > 0:
        return {
            "success": False,
            "error": f"Insufficient stock. Short by {remaining_qty}",
            "consumed_batches": consumed_batches
        }
    
    avg_cost = total_cost / quantity if quantity > 0 else 0
    
    return {
        "success": True,
        "consumed_batches": consumed_batches,
        "total_quantity": quantity,
        "total_cost": total_cost,
        "average_cost": avg_cost
    }


async def create_stock_transaction(
    db: DatabaseHandle,
    item_id: str,
    branch_id: str,
    godown_id: str,
    transaction_type: str,
    quantity: float,
    unit_cost: float,
    total_cost: float,
    batch_id: Optional[str],
    batch_number: Optional[str],
    reference_type: str,
    reference_id: str,
    reference_number: str,
    transaction_date: str,
    narration: Optional[str] = None
) -> Dict[str, Any]:
    """Create stock transaction with running balance"""
    if _is_sql_session(db):
        result = await db.execute(
            select(DBStockTransaction)
            .where(
                DBStockTransaction.item_id == item_id,
                DBStockTransaction.branch_id == branch_id,
                DBStockTransaction.godown_id == godown_id,
            )
            .order_by(desc(DBStockTransaction.created_at))
            .limit(1)
        )
        last_trans = result.scalar_one_or_none()
        running_qty = ((last_trans.running_qty if last_trans else 0) or 0) + quantity
        running_value = ((last_trans.running_value if last_trans else 0) or 0) + total_cost
        transaction_doc = {
            "id": str(uuid.uuid4()),
            "item_id": item_id,
            "branch_id": branch_id,
            "godown_id": godown_id,
            "transaction_type": transaction_type,
            "quantity": quantity,
            "unit_cost": unit_cost,
            "total_cost": total_cost,
            "batch_id": batch_id,
            "batch_number": batch_number,
            "reference_type": reference_type,
            "reference_id": reference_id,
            "reference_number": reference_number,
            "transaction_date": transaction_date,
            "narration": narration,
            "running_qty": running_qty,
            "running_value": running_value,
            "created_at": datetime.now(timezone.utc),
        }
        db.add(DBStockTransaction(**transaction_doc))
        await db.flush()
        transaction_doc["created_at"] = transaction_doc["created_at"].isoformat()
        return transaction_doc
    
    # Get last transaction for running balance
    last_trans = await db.stock_transactions.find_one(
        {"item_id": item_id, "branch_id": branch_id, "godown_id": godown_id},
        sort=[("created_at", -1)]
    )
    
    running_qty = (last_trans["running_qty"] if last_trans else 0) + quantity
    running_value = (last_trans["running_value"] if last_trans else 0) + total_cost
    
    transaction_doc = {
        "id": str(uuid.uuid4()),
        "item_id": item_id,
        "branch_id": branch_id,
        "godown_id": godown_id,
        "transaction_type": transaction_type,
        "quantity": quantity,
        "unit_cost": unit_cost,
        "total_cost": total_cost,
        "batch_id": batch_id,
        "batch_number": batch_number,
        "reference_type": reference_type,
        "reference_id": reference_id,
        "reference_number": reference_number,
        "transaction_date": transaction_date,
        "narration": narration,
        "running_qty": running_qty,
        "running_value": running_value,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.stock_transactions.insert_one(transaction_doc)
    return transaction_doc


async def get_stock_summary(
    db: DatabaseHandle,
    item_id: Optional[str] = None,
    branch_id: Optional[str] = None,
    godown_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Get stock summary with FIFO valuation"""
    if _is_sql_session(db):
        query = select(DBStockBatch).where(DBStockBatch.is_active == True)
        if item_id:
            query = query.where(DBStockBatch.item_id == item_id)
        if branch_id:
            query = query.where(DBStockBatch.branch_id == branch_id)
        if godown_id:
            query = query.where(DBStockBatch.godown_id == godown_id)

        result = await db.execute(query)
        grouped: Dict[tuple, Dict[str, Any]] = {}
        for batch in result.scalars().all():
            key = (batch.item_id, batch.branch_id, batch.godown_id)
            row = grouped.setdefault(key, {"total_quantity": 0.0, "total_value": 0.0, "batch_count": 0})
            remaining = batch.remaining_quantity or 0
            row["total_quantity"] += remaining
            row["total_value"] += remaining * (batch.unit_cost or 0)
            row["batch_count"] += 1

        summaries = []
        for (iid, bid, gid), row in grouped.items():
            item_res = await db.execute(select(DBItem).where(DBItem.id == iid))
            branch_res = await db.execute(select(DBBranch).where(DBBranch.id == bid))
            godown_res = await db.execute(select(DBGodown).where(DBGodown.id == gid))
            item = item_res.scalar_one_or_none()
            branch = branch_res.scalar_one_or_none()
            godown = godown_res.scalar_one_or_none()
            avg_cost = row["total_value"] / row["total_quantity"] if row["total_quantity"] > 0 else 0
            summaries.append({
                "item_id": iid,
                "item_name": item.name if item else "Unknown",
                "item_code": item.code if item else "",
                "branch_id": bid,
                "branch_name": branch.name if branch else "Unknown",
                "godown_id": gid,
                "godown_name": godown.name if godown else "Unknown",
                "total_quantity": row["total_quantity"],
                "total_value": round(row["total_value"], 2),
                "average_cost": round(avg_cost, 2),
                "batch_count": row["batch_count"],
            })
        return summaries
    
    # Build aggregation pipeline
    match_stage = {"is_active": True}
    if item_id:
        match_stage["item_id"] = item_id
    if branch_id:
        match_stage["branch_id"] = branch_id
    if godown_id:
        match_stage["godown_id"] = godown_id
    
    pipeline = [
        {"$match": match_stage},
        {"$group": {
            "_id": {
                "item_id": "$item_id",
                "branch_id": "$branch_id",
                "godown_id": "$godown_id"
            },
            "total_quantity": {"$sum": "$remaining_quantity"},
            "total_value": {"$sum": {"$multiply": ["$remaining_quantity", "$unit_cost"]}},
            "batch_count": {"$sum": 1}
        }}
    ]
    
    results = await db.stock_batches.aggregate(pipeline).to_list(10000)
    
    summaries = []
    for result in results:
        item = await db.items.find_one({"id": result["_id"]["item_id"]}, {"_id": 0})
        branch = await db.branches.find_one({"id": result["_id"]["branch_id"]}, {"_id": 0})
        godown = await db.godowns.find_one({"id": result["_id"]["godown_id"]}, {"_id": 0})
        
        avg_cost = result["total_value"] / result["total_quantity"] if result["total_quantity"] > 0 else 0
        
        summaries.append({
            "item_id": result["_id"]["item_id"],
            "item_name": item["name"] if item else "Unknown",
            "item_code": item["code"] if item else "",
            "branch_id": result["_id"]["branch_id"],
            "branch_name": branch["name"] if branch else "Unknown",
            "godown_id": result["_id"]["godown_id"],
            "godown_name": godown["name"] if godown else "Unknown",
            "total_quantity": result["total_quantity"],
            "total_value": round(result["total_value"], 2),
            "average_cost": round(avg_cost, 2),
            "batch_count": result["batch_count"]
        })
    
    return summaries

def get_item_size_label(item: Optional[Dict[str, Any]]) -> str:
    """Return the best available size label for inventory display."""
    if not item:
        return ""
    return (
        item.get("print_name")
        or item.get("alternate_unit")
        or item.get("unit")
        or ""
    )


def get_movement_label(reference_type: str, quantity: float) -> str:
    """Return a user-friendly inventory movement label."""
    if reference_type == "purchase_invoice":
        return "Inventory In"
    if reference_type == "sales_invoice":
        return "Inventory Out"
    if reference_type == "manual_out":
        return "Inventory Out"
    if reference_type == "delivery_challan":
        return "Dispatch Out"
    if reference_type == "transfer":
        return "Transfer In" if quantity > 0 else "Transfer Out"
    if reference_type == "adjustment":
        return "Adjustment In" if quantity > 0 else "Adjustment Out"
    return reference_type.replace("_", " ").title()


def get_low_stock_threshold(item: Optional[Dict[str, Any]]) -> float:
    """Return the configured low stock alert quantity for an item."""
    if not item:
        return 0

    for field in ("min_stock", "reorder_level"):
        try:
            value = float(item.get(field) or 0)
        except (TypeError, ValueError):
            value = 0
        if value > 0:
            return value

    return 0


async def get_stock_movements(
    db: DatabaseHandle,
    branch_id: Optional[str] = None,
    godown_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Get flattened stock inward/outward movements for inventory screens."""
    if _is_sql_session(db):
        query = select(DBStockTransaction)
        if branch_id:
            query = query.where(DBStockTransaction.branch_id == branch_id)
        if godown_id:
            query = query.where(DBStockTransaction.godown_id == godown_id)
        if start_date:
            query = query.where(DBStockTransaction.transaction_date >= start_date)
        if end_date:
            query = query.where(DBStockTransaction.transaction_date <= end_date)
        query = query.order_by(desc(DBStockTransaction.transaction_date), desc(DBStockTransaction.created_at))

        result = await db.execute(query)
        movements = []
        item_cache = {}
        godown_cache = {}
        for trans in result.scalars().all():
            if trans.item_id not in item_cache:
                item_res = await db.execute(select(DBItem).where(DBItem.id == trans.item_id))
                item_cache[trans.item_id] = _to_dict(item_res.scalar_one_or_none())
            if trans.godown_id and trans.godown_id not in godown_cache:
                godown_res = await db.execute(select(DBGodown).where(DBGodown.id == trans.godown_id))
                godown_cache[trans.godown_id] = _to_dict(godown_res.scalar_one_or_none())
            item = item_cache.get(trans.item_id, {})
            qty = trans.quantity or 0
            balance_qty = trans.running_qty or 0
            low_stock_threshold = get_low_stock_threshold(item)
            movements.append({
                "id": trans.id,
                "date": trans.transaction_date,
                "item_id": trans.item_id,
                "item_name": item.get("name", "Unknown"),
                "size": get_item_size_label(item),
                "godown_name": godown_cache.get(trans.godown_id, {}).get("name", ""),
                "movement_type": get_movement_label(trans.reference_type or "", qty),
                "reference_number": trans.reference_number or "",
                "in_qty": qty if qty > 0 else 0,
                "out_qty": abs(qty) if qty < 0 else 0,
                "balance_qty": balance_qty,
                "low_stock_threshold": round(low_stock_threshold, 2),
                "is_low_stock": low_stock_threshold > 0 and balance_qty <= low_stock_threshold,
            })
        return movements

    query: Dict[str, Any] = {}
    if branch_id:
        query["branch_id"] = branch_id
    if godown_id:
        query["godown_id"] = godown_id

    date_query = {}
    if start_date:
        date_query["$gte"] = start_date
    if end_date:
        date_query["$lte"] = end_date
    if date_query:
        query["transaction_date"] = date_query

    transactions = await db.stock_transactions.find(
        query, {"_id": 0}
    ).sort([("transaction_date", -1), ("created_at", -1)]).to_list(10000)

    item_cache: Dict[str, Dict[str, Any]] = {}
    godown_cache: Dict[str, Dict[str, Any]] = {}
    movements: List[Dict[str, Any]] = []

    for trans in transactions:
        item_id = trans["item_id"]
        godown_id = trans.get("godown_id")

        if item_id not in item_cache:
            item_cache[item_id] = await db.items.find_one({"id": item_id}, {"_id": 0}) or {}
        if godown_id and godown_id not in godown_cache:
            godown_cache[godown_id] = await db.godowns.find_one({"id": godown_id}, {"_id": 0}) or {}

        item = item_cache[item_id]
        godown = godown_cache.get(godown_id, {})
        qty = trans.get("quantity", 0)
        balance_qty = trans.get("running_qty", 0)
        low_stock_threshold = get_low_stock_threshold(item)

        movements.append({
            "id": trans["id"],
            "date": trans["transaction_date"],
            "item_id": item_id,
            "item_name": item.get("name", "Unknown"),
            "size": get_item_size_label(item),
            "godown_name": godown.get("name", ""),
            "movement_type": get_movement_label(trans.get("reference_type", ""), qty),
            "reference_number": trans.get("reference_number", ""),
            "in_qty": qty if qty > 0 else 0,
            "out_qty": abs(qty) if qty < 0 else 0,
            "balance_qty": balance_qty,
            "low_stock_threshold": round(low_stock_threshold, 2),
            "is_low_stock": low_stock_threshold > 0 and balance_qty <= low_stock_threshold,
        })

    return movements


async def get_ready_stock_summary(
    db: DatabaseHandle,
    branch_id: Optional[str] = None,
    godown_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Return simplified ready stock grouped by item."""
    if _is_sql_session(db):
        summary = await get_stock_summary(db, None, branch_id, godown_id)
        ready_stock = []
        for row in summary:
            item_res = await db.execute(select(DBItem).where(DBItem.id == row["item_id"]))
            item = _to_dict(item_res.scalar_one_or_none())
            low_stock_threshold = get_low_stock_threshold(item)
            ready_qty = row.get("total_quantity", 0)
            ready_stock.append({
                "item_id": row["item_id"],
                "item_name": row.get("item_name", "Unknown"),
                "size": get_item_size_label(item),
                "in_qty": 0,
                "out_qty": 0,
                "ready_qty": round(ready_qty, 2),
                "low_stock_threshold": round(low_stock_threshold, 2),
                "is_low_stock": low_stock_threshold > 0 and ready_qty <= low_stock_threshold,
            })
        ready_stock.sort(key=lambda item: item["item_name"].lower())
        return ready_stock

    match_stage: Dict[str, Any] = {"is_active": True}
    if branch_id:
        match_stage["branch_id"] = branch_id
    if godown_id:
        match_stage["godown_id"] = godown_id

    pipeline = [
        {"$match": match_stage},
        {"$group": {
            "_id": "$item_id",
            "ready_quantity": {"$sum": "$remaining_quantity"},
        }}
    ]

    batch_summary = await db.stock_batches.aggregate(pipeline).to_list(10000)
    ready_by_item = {
        row["_id"]: row.get("ready_quantity", 0)
        for row in batch_summary
    }

    trans_query_base: Dict[str, Any] = {}
    if branch_id:
        trans_query_base["branch_id"] = branch_id
    if godown_id:
        trans_query_base["godown_id"] = godown_id

    movement_summary = await db.stock_transactions.aggregate([
        {"$match": trans_query_base},
        {"$group": {
            "_id": "$item_id",
            "in_qty": {
                "$sum": {
                    "$cond": [{"$gt": ["$quantity", 0]}, "$quantity", 0]
                }
            },
            "out_qty": {
                "$sum": {
                    "$cond": [{"$lt": ["$quantity", 0]}, {"$abs": "$quantity"}, 0]
                }
            }
        }}
    ]).to_list(10000)
    movement_by_item = {
        row["_id"]: {
            "in_qty": row.get("in_qty", 0),
            "out_qty": row.get("out_qty", 0),
        }
        for row in movement_summary
    }

    item_cache: Dict[str, Dict[str, Any]] = {}
    ready_stock: List[Dict[str, Any]] = []
    item_ids = set(ready_by_item.keys()) | set(movement_by_item.keys())

    for item_id in item_ids:
        if item_id not in item_cache:
            item_cache[item_id] = await db.items.find_one({"id": item_id}, {"_id": 0}) or {}

        item = item_cache[item_id]
        totals = movement_by_item.get(item_id, {"in_qty": 0, "out_qty": 0})
        ready_qty = totals.get("in_qty", 0) - totals.get("out_qty", 0)
        low_stock_threshold = get_low_stock_threshold(item)

        ready_stock.append({
            "item_id": item_id,
            "item_name": item.get("name", "Unknown"),
            "size": get_item_size_label(item),
            "in_qty": round(totals.get("in_qty", 0), 2),
            "out_qty": round(totals.get("out_qty", 0), 2),
            "ready_qty": round(ready_qty, 2),
            "low_stock_threshold": round(low_stock_threshold, 2),
            "is_low_stock": low_stock_threshold > 0 and ready_qty <= low_stock_threshold,
        })

    ready_stock.sort(key=lambda item: item["item_name"].lower())
    return ready_stock


async def get_stock_ledger(
    db: DatabaseHandle,
    item_id: str,
    branch_id: Optional[str] = None,
    godown_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Dict[str, Any]:
    """Get detailed stock ledger for an item"""
    if _is_sql_session(db):
        query = select(DBStockTransaction).where(DBStockTransaction.item_id == item_id)
        if branch_id:
            query = query.where(DBStockTransaction.branch_id == branch_id)
        if godown_id:
            query = query.where(DBStockTransaction.godown_id == godown_id)
        if start_date:
            query = query.where(DBStockTransaction.transaction_date >= start_date)
        if end_date:
            query = query.where(DBStockTransaction.transaction_date <= end_date)
        query = query.order_by(DBStockTransaction.transaction_date, DBStockTransaction.created_at)

        result = await db.execute(query)
        transactions = result.scalars().all()
        item_res = await db.execute(select(DBItem).where(DBItem.id == item_id))
        item = item_res.scalar_one_or_none()

        opening_qty = 0
        opening_value = 0
        if start_date:
            opening_query = select(DBStockTransaction).where(
                DBStockTransaction.item_id == item_id,
                DBStockTransaction.transaction_date < start_date,
            )
            if branch_id:
                opening_query = opening_query.where(DBStockTransaction.branch_id == branch_id)
            if godown_id:
                opening_query = opening_query.where(DBStockTransaction.godown_id == godown_id)
            opening_query = opening_query.order_by(desc(DBStockTransaction.transaction_date), desc(DBStockTransaction.created_at)).limit(1)
            open_res = await db.execute(opening_query)
            last_before = open_res.scalar_one_or_none()
            opening_qty = last_before.running_qty if last_before else 0
            opening_value = last_before.running_value if last_before else 0

        ledger_entries = []
        for trans in transactions:
            qty = trans.quantity or 0
            ledger_entries.append({
                "date": trans.transaction_date,
                "voucher_number": trans.reference_number,
                "voucher_type": trans.reference_type,
                "batch_number": trans.batch_number,
                "in_qty": qty if qty > 0 else 0,
                "out_qty": abs(qty) if qty < 0 else 0,
                "rate": trans.unit_cost,
                "value": abs(trans.total_cost or 0),
                "balance_qty": trans.running_qty,
                "balance_value": trans.running_value,
            })

        closing_qty = transactions[-1].running_qty if transactions else opening_qty
        closing_value = transactions[-1].running_value if transactions else opening_value
        avg_cost = closing_value / closing_qty if closing_qty and closing_qty > 0 else 0
        return {
            "item_id": item_id,
            "item_name": item.name if item else "Unknown",
            "item_code": item.code if item else "",
            "branch_id": branch_id,
            "godown_id": godown_id,
            "period_start": start_date,
            "period_end": end_date,
            "opening_qty": opening_qty,
            "opening_value": round(opening_value, 2),
            "transactions": ledger_entries,
            "closing_qty": closing_qty,
            "closing_value": round(closing_value, 2),
            "average_cost": round(avg_cost, 2),
        }
    
    # Build query
    query = {"item_id": item_id}
    if branch_id:
        query["branch_id"] = branch_id
    if godown_id:
        query["godown_id"] = godown_id
    
    date_query = {}
    if start_date:
        date_query["$gte"] = start_date
    if end_date:
        date_query["$lte"] = end_date
    if date_query:
        query["transaction_date"] = date_query
    
    # Get transactions
    transactions = await db.stock_transactions.find(
        query, {"_id": 0}
    ).sort("transaction_date", 1).to_list(10000)
    
    # Get item details
    item = await db.items.find_one({"id": item_id}, {"_id": 0})
    
    # Calculate opening balance
    if start_date:
        opening_query = {
            "item_id": item_id,
            "transaction_date": {"$lt": start_date}
        }
        if branch_id:
            opening_query["branch_id"] = branch_id
        if godown_id:
            opening_query["godown_id"] = godown_id
        
        last_before = await db.stock_transactions.find_one(
            opening_query,
            sort=[("transaction_date", -1), ("created_at", -1)]
        )
        opening_qty = last_before["running_qty"] if last_before else 0
        opening_value = last_before["running_value"] if last_before else 0
    else:
        opening_qty = 0
        opening_value = 0
    
    # Format transactions
    ledger_entries = []
    for trans in transactions:
        in_qty = trans["quantity"] if trans["quantity"] > 0 else 0
        out_qty = abs(trans["quantity"]) if trans["quantity"] < 0 else 0
        
        ledger_entries.append({
            "date": trans["transaction_date"],
            "voucher_number": trans["reference_number"],
            "voucher_type": trans["reference_type"],
            "batch_number": trans.get("batch_number"),
            "in_qty": in_qty,
            "out_qty": out_qty,
            "rate": trans["unit_cost"],
            "value": abs(trans["total_cost"]),
            "balance_qty": trans["running_qty"],
            "balance_value": trans["running_value"]
        })
    
    closing_qty = transactions[-1]["running_qty"] if transactions else opening_qty
    closing_value = transactions[-1]["running_value"] if transactions else opening_value
    avg_cost = closing_value / closing_qty if closing_qty > 0 else 0
    
    return {
        "item_id": item_id,
        "item_name": item["name"] if item else "Unknown",
        "item_code": item["code"] if item else "",
        "branch_id": branch_id,
        "godown_id": godown_id,
        "period_start": start_date,
        "period_end": end_date,
        "opening_qty": opening_qty,
        "opening_value": round(opening_value, 2),
        "transactions": ledger_entries,
        "closing_qty": closing_qty,
        "closing_value": round(closing_value, 2),
        "average_cost": round(avg_cost, 2)
    }


async def process_stock_adjustment(
    db: DatabaseHandle,
    adjustment_data: Dict[str, Any],
    created_by: str
) -> Dict[str, Any]:
    """Process stock adjustment with accounting impact"""
    if _is_sql_session(db):
        result = await db.execute(select(DBStockAdjustment).order_by(desc(DBStockAdjustment.created_at)).limit(1))
        last_adj = result.scalar_one_or_none()
        if last_adj:
            try:
                new_num = int(last_adj.adjustment_number.split("/")[-1]) + 1
            except (ValueError, IndexError, AttributeError):
                new_num = 1
        else:
            new_num = 1

        adjustment_number = f"ADJ/2025-26/{new_num:05d}"
        total_shortage = 0.0
        total_excess = 0.0
        for item in adjustment_data["items"]:
            diff = item["difference"]
            unit_cost = item.get("unit_cost", item.get("rate", 0))
            value_diff = item.get("value_difference", item.get("value", abs(diff) * unit_cost))
            if diff < 0:
                total_shortage += abs(value_diff)
                await consume_stock_fifo(
                    db, item["item_id"], adjustment_data["branch_id"], adjustment_data["godown_id"],
                    abs(diff), "adjustment", adjustment_number, adjustment_number,
                    adjustment_data["adjustment_date"],
                )
            elif diff > 0:
                total_excess += value_diff
                batch_number = await get_next_batch_number(db, item["item_id"], adjustment_data["branch_id"])
                await create_stock_batch(
                    db, item["item_id"], adjustment_data["branch_id"], adjustment_data["godown_id"],
                    batch_number, diff, unit_cost, adjustment_data["adjustment_date"],
                    None, None, None, "adjustment", adjustment_number, adjustment_number,
                )

        adjustment_doc = {
            "id": str(uuid.uuid4()),
            "adjustment_number": adjustment_number,
            "branch_id": adjustment_data["branch_id"],
            "godown_id": adjustment_data["godown_id"],
            "adjustment_date": adjustment_data["adjustment_date"],
            "reason": adjustment_data["reason"],
            "items": adjustment_data["items"],
            "narration": adjustment_data.get("narration") or adjustment_data.get("remarks"),
            "total_shortage": total_shortage,
            "total_excess": total_excess,
            "net_value": total_excess - total_shortage,
            "status": "completed",
            "created_by": created_by,
            "created_at": datetime.now(timezone.utc),
        }
        db.add(DBStockAdjustment(**adjustment_doc))
        await db.commit()
        adjustment_doc["created_at"] = adjustment_doc["created_at"].isoformat()
        return adjustment_doc
    
    # Generate adjustment number
    last_adj = await db.stock_adjustments.find_one(sort=[("created_at", -1)])
    if last_adj:
        try:
            last_num = int(last_adj["adjustment_number"].split("/")[-1])
            new_num = last_num + 1
        except:
            new_num = 1
    else:
        new_num = 1
    
    adjustment_number = f"ADJ/2025-26/{new_num:05d}"
    
    total_shortage = 0.0
    total_excess = 0.0
    
    for item in adjustment_data["items"]:
        diff = item["difference"]
        unit_cost = item.get("unit_cost", item.get("rate", 0))
        value_diff = item.get("value_difference", item.get("value", abs(diff) * unit_cost))
        
        if diff < 0:  # Shortage
            total_shortage += abs(value_diff)
            # Consume stock
            await consume_stock_fifo(
                db, item["item_id"], adjustment_data["branch_id"],
                adjustment_data["godown_id"], abs(diff),
                "adjustment", adjustment_number, adjustment_number,
                adjustment_data["adjustment_date"]
            )
        elif diff > 0:  # Excess
            total_excess += value_diff
            # Create new batch
            batch_number = await get_next_batch_number(
                db, item["item_id"], adjustment_data["branch_id"]
            )
            await create_stock_batch(
                db, item["item_id"], adjustment_data["branch_id"],
                adjustment_data["godown_id"], batch_number, diff,
                unit_cost, adjustment_data["adjustment_date"],
                None, None, None, "adjustment", adjustment_number, adjustment_number
            )
    
    # Create adjustment document
    adjustment_doc = {
        "id": str(uuid.uuid4()),
        "adjustment_number": adjustment_number,
        "branch_id": adjustment_data["branch_id"],
        "godown_id": adjustment_data["godown_id"],
        "adjustment_date": adjustment_data["adjustment_date"],
        "reason": adjustment_data["reason"],
        "items": adjustment_data["items"],
        "narration": adjustment_data.get("narration") or adjustment_data.get("remarks"),
        "total_shortage": total_shortage,
        "total_excess": total_excess,
        "net_value": total_excess - total_shortage,
        "status": "completed",
        "created_by": created_by,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.stock_adjustments.insert_one(adjustment_doc)
    
    return adjustment_doc


async def process_inter_branch_transfer(
    db: DatabaseHandle,
    transfer_data: Dict[str, Any],
    created_by: str
) -> Dict[str, Any]:
    """Process inter-branch stock transfer"""
    if _is_sql_session(db):
        result = await db.execute(select(DBInterBranchTransfer).order_by(desc(DBInterBranchTransfer.created_at)).limit(1))
        last_transfer = result.scalar_one_or_none()
        if last_transfer:
            try:
                new_num = int(last_transfer.transfer_number.split("/")[-1]) + 1
            except (ValueError, IndexError, AttributeError):
                new_num = 1
        else:
            new_num = 1

        transfer_number = f"IBT/2025-26/{new_num:05d}"
        total_quantity = 0.0
        total_value = 0.0
        processed_items = []

        for item in transfer_data["items"]:
            consume_result = await consume_stock_fifo(
                db, item["item_id"], transfer_data["from_branch_id"],
                transfer_data["from_godown_id"], item["quantity"],
                "transfer", transfer_number, transfer_number,
                transfer_data["transfer_date"],
            )
            if not consume_result["success"]:
                return {"success": False, "error": consume_result["error"]}

            batch_number = await get_next_batch_number(db, item["item_id"], transfer_data["to_branch_id"])
            await create_stock_batch(
                db, item["item_id"], transfer_data["to_branch_id"], transfer_data["to_godown_id"],
                batch_number, item["quantity"], consume_result["average_cost"],
                transfer_data["transfer_date"], None, None, None,
                "transfer", transfer_number, transfer_number,
            )

            total_quantity += item["quantity"]
            total_value += consume_result["total_cost"]
            processed_items.append({**item, "unit_cost": consume_result["average_cost"], "total_cost": consume_result["total_cost"]})

        transfer_doc = {
            "id": str(uuid.uuid4()),
            "transfer_number": transfer_number,
            "from_branch_id": transfer_data["from_branch_id"],
            "to_branch_id": transfer_data["to_branch_id"],
            "from_godown_id": transfer_data["from_godown_id"],
            "to_godown_id": transfer_data["to_godown_id"],
            "transfer_date": transfer_data["transfer_date"],
            "items": processed_items,
            "narration": transfer_data.get("narration"),
            "total_quantity": total_quantity,
            "total_value": total_value,
            "status": "completed",
            "created_by": created_by,
            "created_at": datetime.now(timezone.utc),
        }
        db.add(DBInterBranchTransfer(**transfer_doc))
        await db.commit()
        transfer_doc["created_at"] = transfer_doc["created_at"].isoformat()
        return {"success": True, "transfer": transfer_doc}
    
    # Generate transfer number
    last_transfer = await db.inter_branch_transfers.find_one(sort=[("created_at", -1)])
    if last_transfer:
        try:
            last_num = int(last_transfer["transfer_number"].split("/")[-1])
            new_num = last_num + 1
        except:
            new_num = 1
    else:
        new_num = 1
    
    transfer_number = f"IBT/2025-26/{new_num:05d}"
    
    total_quantity = 0.0
    total_value = 0.0
    processed_items = []
    
    for item in transfer_data["items"]:
        # Consume from source using FIFO
        consume_result = await consume_stock_fifo(
            db, item["item_id"], transfer_data["from_branch_id"],
            transfer_data["from_godown_id"], item["quantity"],
            "transfer", transfer_number, transfer_number,
            transfer_data["transfer_date"]
        )
        
        if not consume_result["success"]:
            return {"success": False, "error": consume_result["error"]}
        
        # Create batch at destination
        batch_number = await get_next_batch_number(
            db, item["item_id"], transfer_data["to_branch_id"]
        )
        await create_stock_batch(
            db, item["item_id"], transfer_data["to_branch_id"],
            transfer_data["to_godown_id"], batch_number, item["quantity"],
            consume_result["average_cost"], transfer_data["transfer_date"],
            None, None, None, "transfer", transfer_number, transfer_number
        )
        
        total_quantity += item["quantity"]
        total_value += consume_result["total_cost"]
        
        processed_items.append({
            **item,
            "unit_cost": consume_result["average_cost"],
            "total_cost": consume_result["total_cost"]
        })
    
    # Create transfer document
    transfer_doc = {
        "id": str(uuid.uuid4()),
        "transfer_number": transfer_number,
        "from_branch_id": transfer_data["from_branch_id"],
        "to_branch_id": transfer_data["to_branch_id"],
        "from_godown_id": transfer_data["from_godown_id"],
        "to_godown_id": transfer_data["to_godown_id"],
        "transfer_date": transfer_data["transfer_date"],
        "items": processed_items,
        "narration": transfer_data.get("narration"),
        "total_quantity": total_quantity,
        "total_value": total_value,
        "status": "completed",
        "created_by": created_by,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.inter_branch_transfers.insert_one(transfer_doc)
    
    return {"success": True, "transfer": transfer_doc}


async def get_item_profitability(
    db: DatabaseHandle,
    item_id: Optional[str] = None,
    branch_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Calculate item-wise profitability"""
    if _is_sql_session(db):
        # Sales are still kept by legacy routes, so ORM-only profitability has no
        # sales source yet. Return an empty set for now.
        return []
    
    # Build sales query
    sales_query = {"status": "completed"}
    if branch_id:
        sales_query["branch_id"] = branch_id
    if start_date:
        sales_query["invoice_date"] = {"$gte": start_date}
    if end_date:
        if "invoice_date" in sales_query:
            sales_query["invoice_date"]["$lte"] = end_date
        else:
            sales_query["invoice_date"] = {"$lte": end_date}
    
    sales = await db.sales_invoices.find(sales_query, {"_id": 0}).to_list(10000)
    
    # Aggregate by item
    item_stats = {}
    
    for invoice in sales:
        for item in invoice["items"]:
            iid = item["item_id"]
            if item_id and iid != item_id:
                continue
            
            if iid not in item_stats:
                item_stats[iid] = {
                    "item_id": iid,
                    "item_name": item["item_name"],
                    "qty_sold": 0,
                    "sales_value": 0,
                    "cost_value": 0
                }
            
            item_stats[iid]["qty_sold"] += item["quantity"]
            item_stats[iid]["sales_value"] += item["taxable_amount"]
    
    # Get cost from stock transactions
    for iid, stats in item_stats.items():
        # Get average cost from stock batches
        batches = await db.stock_batches.find({"item_id": iid}).to_list(1000)
        if batches:
            total_value = sum(b["remaining_quantity"] * b["unit_cost"] for b in batches)
            total_qty = sum(b["remaining_quantity"] for b in batches)
            avg_cost = total_value / total_qty if total_qty > 0 else 0
        else:
            # Fallback to item cost price
            item = await db.items.find_one({"id": iid})
            avg_cost = item["cost_price"] if item else 0
        
        stats["cost_value"] = stats["qty_sold"] * avg_cost
        stats["profit"] = stats["sales_value"] - stats["cost_value"]
        stats["margin_percent"] = (stats["profit"] / stats["sales_value"] * 100) if stats["sales_value"] > 0 else 0
    
    return list(item_stats.values())
