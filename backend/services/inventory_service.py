"""
HOOREN ERP - Inventory Services
FIFO valuation, batch tracking, stock management
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase
import uuid


async def get_next_batch_number(
    db: AsyncIOMotorDatabase,
    item_id: str,
    branch_id: str
) -> str:
    """Generate next batch number for item"""
    
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
    db: AsyncIOMotorDatabase,
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
    return batch_doc


async def consume_stock_fifo(
    db: AsyncIOMotorDatabase,
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
    db: AsyncIOMotorDatabase,
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
    db: AsyncIOMotorDatabase,
    item_id: Optional[str] = None,
    branch_id: Optional[str] = None,
    godown_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Get stock summary with FIFO valuation"""
    
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


async def get_stock_ledger(
    db: AsyncIOMotorDatabase,
    item_id: str,
    branch_id: Optional[str] = None,
    godown_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Dict[str, Any]:
    """Get detailed stock ledger for an item"""
    
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
    db: AsyncIOMotorDatabase,
    adjustment_data: Dict[str, Any],
    created_by: str
) -> Dict[str, Any]:
    """Process stock adjustment with accounting impact"""
    
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
        value_diff = item["value_difference"]
        
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
                item["unit_cost"], adjustment_data["adjustment_date"],
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
        "narration": adjustment_data.get("narration"),
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
    db: AsyncIOMotorDatabase,
    transfer_data: Dict[str, Any],
    created_by: str
) -> Dict[str, Any]:
    """Process inter-branch stock transfer"""
    
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
    db: AsyncIOMotorDatabase,
    item_id: Optional[str] = None,
    branch_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Calculate item-wise profitability"""
    
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
