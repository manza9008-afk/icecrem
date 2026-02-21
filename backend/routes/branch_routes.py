"""
HOOREN ERP - Branch & Godown Routes
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime, timezone
import uuid

router = APIRouter(prefix="/api/branches", tags=["branches"])

# Import db from server
from server import db
from utils import get_current_user


@router.post("")
async def create_branch(branch_data: dict, current_user: dict = Depends(get_current_user)):
    """Create a new branch"""
    # Check if code exists
    existing = await db.branches.find_one({"code": branch_data["code"]})
    if existing:
        raise HTTPException(status_code=400, detail="Branch code already exists")
    
    branch_doc = {
        "id": str(uuid.uuid4()),
        **branch_data,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.branches.insert_one(branch_doc)
    
    # Create default godown for this branch
    godown_doc = {
        "id": str(uuid.uuid4()),
        "code": f"{branch_data['code']}-MAIN",
        "name": "Main Godown",
        "branch_id": branch_doc["id"],
        "address": branch_data.get("address", ""),
        "is_default": True,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.godowns.insert_one(godown_doc)
    
    branch_doc.pop("_id", None)
    return branch_doc


@router.get("", response_model=List[dict])
async def get_branches(
    is_active: bool = True,
    current_user: dict = Depends(get_current_user)
):
    """Get all branches"""
    query = {}
    if is_active is not None:
        query["is_active"] = is_active
    
    branches = await db.branches.find(query, {"_id": 0}).to_list(100)
    return branches


@router.get("/{branch_id}")
async def get_branch(branch_id: str, current_user: dict = Depends(get_current_user)):
    """Get branch by ID"""
    branch = await db.branches.find_one({"id": branch_id}, {"_id": 0})
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    return branch


@router.put("/{branch_id}")
async def update_branch(
    branch_id: str,
    branch_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Update branch"""
    existing = await db.branches.find_one({"id": branch_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Branch not found")
    
    # Check code uniqueness
    if "code" in branch_data:
        code_exists = await db.branches.find_one({
            "code": branch_data["code"],
            "id": {"$ne": branch_id}
        })
        if code_exists:
            raise HTTPException(status_code=400, detail="Branch code already exists")
    
    branch_data["modified_at"] = datetime.now(timezone.utc).isoformat()
    await db.branches.update_one({"id": branch_id}, {"$set": branch_data})
    
    return {"message": "Branch updated successfully"}


@router.delete("/{branch_id}")
async def delete_branch(branch_id: str, current_user: dict = Depends(get_current_user)):
    """Soft delete branch"""
    existing = await db.branches.find_one({"id": branch_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Branch not found")
    
    # Check if branch has transactions
    voucher_count = await db.vouchers.count_documents({"branch_id": branch_id})
    if voucher_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete branch with {voucher_count} vouchers"
        )
    
    await db.branches.update_one(
        {"id": branch_id},
        {"$set": {"is_active": False}}
    )
    
    return {"message": "Branch deleted successfully"}


# ==================== GODOWNS ====================

@router.post("/{branch_id}/godowns")
async def create_godown(
    branch_id: str,
    godown_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Create a godown for a branch"""
    branch = await db.branches.find_one({"id": branch_id})
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    
    # Check code uniqueness
    existing = await db.godowns.find_one({
        "code": godown_data["code"],
        "branch_id": branch_id
    })
    if existing:
        raise HTTPException(status_code=400, detail="Godown code already exists")
    
    godown_doc = {
        "id": str(uuid.uuid4()),
        "branch_id": branch_id,
        **godown_data,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.godowns.insert_one(godown_doc)
    godown_doc.pop("_id", None)
    return godown_doc


@router.get("/{branch_id}/godowns")
async def get_godowns(
    branch_id: str,
    is_active: bool = True,
    current_user: dict = Depends(get_current_user)
):
    """Get godowns for a branch"""
    query = {"branch_id": branch_id}
    if is_active is not None:
        query["is_active"] = is_active
    
    godowns = await db.godowns.find(query, {"_id": 0}).to_list(200)
    return godowns


@router.get("/godowns/all")
async def get_all_godowns(
    is_active: bool = True,
    current_user: dict = Depends(get_current_user)
):
    """Get all godowns across branches"""
    query = {}
    if is_active is not None:
        query["is_active"] = is_active
    
    godowns = await db.godowns.find(query, {"_id": 0}).to_list(500)
    
    # Enrich with branch info
    for godown in godowns:
        branch = await db.branches.find_one({"id": godown["branch_id"]}, {"_id": 0})
        godown["branch_name"] = branch["name"] if branch else "Unknown"
    
    return godowns


@router.put("/godowns/{godown_id}")
async def update_godown(
    godown_id: str,
    godown_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Update godown"""
    existing = await db.godowns.find_one({"id": godown_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Godown not found")
    
    godown_data["modified_at"] = datetime.now(timezone.utc).isoformat()
    await db.godowns.update_one({"id": godown_id}, {"$set": godown_data})
    
    return {"message": "Godown updated successfully"}


@router.delete("/godowns/{godown_id}")
async def delete_godown(godown_id: str, current_user: dict = Depends(get_current_user)):
    """Soft delete godown"""
    existing = await db.godowns.find_one({"id": godown_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Godown not found")
    
    # Check if godown has stock
    batch_count = await db.stock_batches.count_documents({
        "godown_id": godown_id,
        "remaining_quantity": {"$gt": 0}
    })
    if batch_count > 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete godown with stock"
        )
    
    await db.godowns.update_one(
        {"id": godown_id},
        {"$set": {"is_active": False}}
    )
    
    return {"message": "Godown deleted successfully"}
