from typing import List, Tuple
from datetime import datetime

async def compute_fifo_cost(db, item_id: str, branch_id: str, godown_id: str, quantity: float) -> Tuple[float, List[dict]]:
    """Compute FIFO cost and allocate from batches"""
    # Get available batches (FIFO order)
    batches = await db.stock_batches.find({
        "item_id": item_id,
        "branch_id": branch_id,
        "godown_id": godown_id,
        "remaining_quantity": {"$gt": 0}
    }).sort("purchase_date", 1).to_list(1000)
    
    if not batches:
        raise ValueError(f"No stock available for item {item_id}")
    
    total_cost = 0
    remaining_to_allocate = quantity
    allocations = []
    
    for batch in batches:
        if remaining_to_allocate <= 0:
            break
        
        allocated_qty = min(batch["remaining_quantity"], remaining_to_allocate)
        batch_cost = allocated_qty * batch["unit_cost"]
        total_cost += batch_cost
        
        allocations.append({
            "batch_id": batch["id"],
            "batch_number": batch["batch_number"],
            "quantity": allocated_qty,
            "unit_cost": batch["unit_cost"],
            "total_cost": batch_cost
        })
        
        remaining_to_allocate -= allocated_qty
    
    if remaining_to_allocate > 0:
        raise ValueError(f"Insufficient stock. Required: {quantity}, Available: {quantity - remaining_to_allocate}")
    
    return total_cost, allocations

async def update_batch_quantities(db, allocations: List[dict]):
    """Update remaining quantities in batches after allocation"""
    for alloc in allocations:
        await db.stock_batches.update_one(
            {"id": alloc["batch_id"]},
            {"$inc": {"remaining_quantity": -alloc["quantity"]}}
        )

async def get_stock_valuation(db, item_id: str, branch_id: str = None, godown_id: str = None):
    """Get current stock valuation using FIFO"""
    query = {"item_id": item_id, "remaining_quantity": {"$gt": 0}}
    if branch_id:
        query["branch_id"] = branch_id
    if godown_id:
        query["godown_id"] = godown_id
    
    batches = await db.stock_batches.find(query).to_list(1000)
    
    total_quantity = sum(b["remaining_quantity"] for b in batches)
    total_value = sum(b["remaining_quantity"] * b["unit_cost"] for b in batches)
    average_cost = total_value / total_quantity if total_quantity > 0 else 0
    
    return {
        "total_quantity": total_quantity,
        "total_value": total_value,
        "average_cost": average_cost,
        "batches": batches
    }

async def validate_stock_availability(db, item_id: str, branch_id: str, godown_id: str, quantity: float):
    """Validate sufficient stock exists"""
    current_stock = await db.stock_batches.aggregate([
        {
            "$match": {
                "item_id": item_id,
                "branch_id": branch_id,
                "godown_id": godown_id,
                "remaining_quantity": {"$gt": 0}
            }
        },
        {
            "$group": {
                "_id": None,
                "total": {"$sum": "$remaining_quantity"}
            }
        }
    ]).to_list(1)
    
    available = current_stock[0]["total"] if current_stock else 0
    
    if available < quantity:
        raise ValueError(f"Insufficient stock. Available: {available}, Required: {quantity}")
    
    return True
