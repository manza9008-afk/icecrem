from fastapi import APIRouter, HTTPException, Depends
from typing import List
from models_accounting import (
    AccountGroupCreate, AccountGroup, AccountGroupTree,
    LedgerCreate, Ledger,
    VoucherCreate, Voucher, VoucherEntryItem,
    BranchCreate, Branch,
    GodownCreate, Godown
)
from utils import get_current_user
from motor.motor_asyncio import AsyncIOMotorDatabase
import uuid
from datetime import datetime, timezone

router = APIRouter(prefix="/api/accounting", tags=["accounting"])

# Dependency to get database
from server import db

# ==================== ACCOUNT GROUPS ====================

@router.post("/account-groups", response_model=AccountGroup)
async def create_account_group(group: AccountGroupCreate, current_user: dict = Depends(get_current_user)):
    # Check if code already exists
    existing = await db.account_groups.find_one({"code": group.code})
    if existing:
        raise HTTPException(status_code=400, detail="Account group code already exists")
    
    # Validate parent if specified
    if group.parent_id:
        parent = await db.account_groups.find_one({"id": group.parent_id}, {"_id": 0})
        if not parent:
            raise HTTPException(status_code=404, detail="Parent account group not found")
    
    group_obj = AccountGroup(**group.model_dump())
    doc = group_obj.model_dump()
    await db.account_groups.insert_one(doc)
    
    return group_obj

@router.get("/account-groups", response_model=List[AccountGroup])
async def get_account_groups(current_user: dict = Depends(get_current_user)):
    groups = await db.account_groups.find({"is_active": True}, {"_id": 0}).to_list(1000)
    return groups

@router.get("/account-groups/tree", response_model=List[AccountGroupTree])
async def get_account_groups_tree(current_user: dict = Depends(get_current_user)):
    """Get account groups in hierarchical tree structure"""
    all_groups = await db.account_groups.find({"is_active": True}, {"_id": 0}).to_list(1000)
    
    # Build tree structure
    groups_dict = {g['id']: {**g, 'children': []} for g in all_groups}
    tree = []
    
    for group in all_groups:
        if group.get('parent_id'):
            parent = groups_dict.get(group['parent_id'])
            if parent:
                parent['children'].append(groups_dict[group['id']])
        else:
            tree.append(groups_dict[group['id']])
    
    return tree

@router.put("/account-groups/{group_id}", response_model=AccountGroup)
async def update_account_group(group_id: str, group: AccountGroupCreate, current_user: dict = Depends(get_current_user)):
    existing = await db.account_groups.find_one({"id": group_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Account group not found")
    
    update_data = group.model_dump()
    await db.account_groups.update_one({"id": group_id}, {"$set": update_data})
    
    updated = await db.account_groups.find_one({"id": group_id}, {"_id": 0})
    return updated

@router.delete("/account-groups/{group_id}")
async def delete_account_group(group_id: str, current_user: dict = Depends(get_current_user)):
    # Check if any ledgers are using this group
    ledgers_count = await db.ledgers.count_documents({"account_group_id": group_id})
    if ledgers_count > 0:
        raise HTTPException(status_code=400, detail=f"Cannot delete. {ledgers_count} ledgers are using this account group")
    
    result = await db.account_groups.update_one(
        {"id": group_id},
        {"$set": {"is_active": False}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Account group not found")
    
    return {"message": "Account group deleted successfully"}

# ==================== LEDGERS ====================

@router.post("/ledgers", response_model=Ledger)
async def create_ledger(ledger: LedgerCreate, current_user: dict = Depends(get_current_user)):
    # Validate account group exists
    group = await db.account_groups.find_one({"id": ledger.account_group_id}, {"_id": 0})
    if not group:
        raise HTTPException(status_code=404, detail="Account group not found")
    
    ledger_obj = Ledger(**ledger.model_dump())
    
    # Set current balance to opening balance
    ledger_obj.current_balance = ledger.opening_balance
    
    doc = ledger_obj.model_dump()
    await db.ledgers.insert_one(doc)
    
    # Post opening balance voucher if not zero
    if ledger.opening_balance != 0:
        voucher_entry = {
            "id": str(uuid.uuid4()),
            "voucher_type": "journal",
            "voucher_number": f"OB/{ledger_obj.id[:8]}",
            "voucher_date": datetime.now(timezone.utc).isoformat(),
            "entries": [
                {
                    "ledger_id": ledger_obj.id,
                    "ledger_name": ledger_obj.name,
                    "entry_type": ledger.balance_type,
                    "amount": abs(ledger.opening_balance),
                    "narration": "Opening Balance"
                }
            ],
            "narration": "Opening Balance Entry",
            "total_amount": abs(ledger.opening_balance),
            "is_approved": True,
            "created_by": current_user["username"],
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.vouchers.insert_one(voucher_entry)
    
    return ledger_obj

@router.get("/ledgers", response_model=List[Ledger])
async def get_ledgers(
    branch_id: str = None,
    account_group_id: str = None,
    current_user: dict = Depends(get_current_user)
):
    query = {"is_active": True}
    if branch_id:
        query["branch_id"] = branch_id
    if account_group_id:
        query["account_group_id"] = account_group_id
    
    ledgers = await db.ledgers.find(query, {"_id": 0}).to_list(1000)
    return ledgers

@router.get("/ledgers/{ledger_id}", response_model=Ledger)
async def get_ledger(ledger_id: str, current_user: dict = Depends(get_current_user)):
    ledger = await db.ledgers.find_one({"id": ledger_id}, {"_id": 0})
    if not ledger:
        raise HTTPException(status_code=404, detail="Ledger not found")
    return ledger

@router.put("/ledgers/{ledger_id}", response_model=Ledger)
async def update_ledger(ledger_id: str, ledger: LedgerCreate, current_user: dict = Depends(get_current_user)):
    existing = await db.ledgers.find_one({"id": ledger_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Ledger not found")
    
    # Validate account group
    group = await db.account_groups.find_one({"id": ledger.account_group_id})
    if not group:
        raise HTTPException(status_code=404, detail="Account group not found")
    
    update_data = ledger.model_dump(exclude={"opening_balance"})  # Don't update opening balance
    await db.ledgers.update_one({"id": ledger_id}, {"$set": update_data})
    
    updated = await db.ledgers.find_one({"id": ledger_id}, {"_id": 0})
    return updated

@router.delete("/ledgers/{ledger_id}")
async def delete_ledger(ledger_id: str, current_user: dict = Depends(get_current_user)):
    # Check if any voucher entries use this ledger
    voucher_count = await db.vouchers.count_documents({"entries.ledger_id": ledger_id})
    if voucher_count > 0:
        raise HTTPException(status_code=400, detail=f"Cannot delete. Ledger is used in {voucher_count} vouchers")
    
    result = await db.ledgers.update_one(
        {"id": ledger_id},
        {"$set": {"is_active": False}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Ledger not found")
    
    return {"message": "Ledger deleted successfully"}

# ==================== BRANCHES ====================

@router.post("/branches", response_model=Branch)
async def create_branch(branch: BranchCreate, current_user: dict = Depends(get_current_user)):
    # Check if code exists
    existing = await db.branches.find_one({"code": branch.code})
    if existing:
        raise HTTPException(status_code=400, detail="Branch code already exists")
    
    branch_obj = Branch(**branch.model_dump())
    doc = branch_obj.model_dump()
    await db.branches.insert_one(doc)
    
    return branch_obj

@router.get("/branches", response_model=List[Branch])
async def get_branches(current_user: dict = Depends(get_current_user)):
    branches = await db.branches.find({"is_active": True}, {"_id": 0}).to_list(100)
    return branches

@router.put("/branches/{branch_id}")
async def update_branch(branch_id: str, branch: BranchCreate, current_user: dict = Depends(get_current_user)):
    result = await db.branches.update_one({"id": branch_id}, {"$set": branch.model_dump()})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Branch not found")
    return {"message": "Branch updated successfully"}

# ==================== GODOWNS ====================

@router.post("/godowns", response_model=Godown)
async def create_godown(godown: GodownCreate, current_user: dict = Depends(get_current_user)):
    # Validate branch
    branch = await db.branches.find_one({"id": godown.branch_id})
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    
    godown_obj = Godown(**godown.model_dump())
    doc = godown_obj.model_dump()
    await db.godowns.insert_one(doc)
    
    return godown_obj

@router.get("/godowns", response_model=List[Godown])
async def get_godowns(branch_id: str = None, current_user: dict = Depends(get_current_user)):
    query = {"is_active": True}
    if branch_id:
        query["branch_id"] = branch_id
    
    godowns = await db.godowns.find(query, {"_id": 0}).to_list(200)
    return godowns
