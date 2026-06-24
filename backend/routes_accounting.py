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
import uuid
from datetime import datetime, timezone
import json

router = APIRouter(prefix="/api/accounting", tags=["accounting"])

from database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from db_models import AccountGroup as DBAccountGroup, Ledger as DBLedger, Branch as DBBranch, Godown as DBGodown, Voucher as DBVoucher

def to_dict(obj):
    if not obj: return {}
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}

# ==================== ACCOUNT GROUPS ====================

@router.post("/account-groups", response_model=AccountGroup)
async def create_account_group(group: AccountGroupCreate, current_user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    # Check if code already exists
    result = await session.execute(select(DBAccountGroup).where(DBAccountGroup.code == group.code))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Account group code already exists")
    
    # Validate parent if specified
    if group.parent_id:
        parent_result = await session.execute(select(DBAccountGroup).where(DBAccountGroup.id == group.parent_id))
        parent = parent_result.scalar_one_or_none()
        if not parent:
            raise HTTPException(status_code=404, detail="Parent account group not found")
    
    new_group = DBAccountGroup(id=str(uuid.uuid4()), **group.model_dump(), is_active=True, created_at=datetime.now(timezone.utc))
    session.add(new_group)
    await session.commit()
    
    return to_dict(new_group)

@router.get("/account-groups", response_model=List[AccountGroup])
async def get_account_groups(current_user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(DBAccountGroup).where(DBAccountGroup.is_active == True))
    groups = result.scalars().all()
    return [to_dict(g) for g in groups]

@router.get("/account-groups/tree", response_model=List[AccountGroupTree])
async def get_account_groups_tree(current_user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    """Get account groups in hierarchical tree structure"""
    result = await session.execute(select(DBAccountGroup).where(DBAccountGroup.is_active == True))
    all_groups = [to_dict(g) for g in result.scalars().all()]
    
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
async def update_account_group(group_id: str, group: AccountGroupCreate, current_user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(DBAccountGroup).where(DBAccountGroup.id == group_id))
    existing = result.scalar_one_or_none()
    if not existing:
        raise HTTPException(status_code=404, detail="Account group not found")
    
    for key, value in group.model_dump().items():
        setattr(existing, key, value)
    await session.commit()
    
    return to_dict(existing)

@router.delete("/account-groups/{group_id}")
async def delete_account_group(group_id: str, current_user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    # Check if any ledgers are using this group
    res = await session.execute(select(func.count(DBLedger.id)).where(DBLedger.account_group_id == group_id))
    ledgers_count = res.scalar() or 0
    if ledgers_count > 0:
        raise HTTPException(status_code=400, detail=f"Cannot delete. {ledgers_count} ledgers are using this account group")
    
    result = await session.execute(select(DBAccountGroup).where(DBAccountGroup.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Account group not found")
    
    group.is_active = False
    await session.commit()
    return {"message": "Account group deleted successfully"}

# ==================== LEDGERS ====================

@router.post("/ledgers", response_model=Ledger)
async def create_ledger(ledger: LedgerCreate, current_user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    # Validate account group exists
    res_group = await session.execute(select(DBAccountGroup).where(DBAccountGroup.id == ledger.account_group_id))
    group = res_group.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Account group not found")
    
    new_ledger = DBLedger(
        id=str(uuid.uuid4()),
        **ledger.model_dump(),
        current_balance=ledger.opening_balance,
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )
    session.add(new_ledger)
    
    # Post opening balance voucher if not zero
    if ledger.opening_balance != 0:
        voucher_entry = DBVoucher(
            id=str(uuid.uuid4()),
            voucher_type="journal",
            voucher_number=f"OB/{new_ledger.id[:8]}",
            voucher_date=datetime.now(timezone.utc).isoformat()[:10],
            entries=json.dumps([
                {
                    "ledger_id": new_ledger.id,
                    "ledger_name": new_ledger.name,
                    "entry_type": ledger.balance_type,
                    "amount": abs(ledger.opening_balance),
                    "narration": "Opening Balance"
                }
            ]),
            narration="Opening Balance Entry",
            total_debit=abs(ledger.opening_balance) if ledger.balance_type == "debit" else 0.0,
            total_credit=abs(ledger.opening_balance) if ledger.balance_type == "credit" else 0.0,
            is_approved=True,
            created_by=current_user["username"],
            created_at=datetime.now(timezone.utc)
        )
        session.add(voucher_entry)
    
    await session.commit()
    return to_dict(new_ledger)

@router.get("/ledgers", response_model=List[Ledger])
async def get_ledgers(
    branch_id: str = None,
    account_group_id: str = None,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    query = select(DBLedger).where(DBLedger.is_active == True)
    if branch_id:
        query = query.where(DBLedger.branch_id == branch_id)
    if account_group_id:
        query = query.where(DBLedger.account_group_id == account_group_id)
    
    result = await session.execute(query)
    ledgers = result.scalars().all()
    return [to_dict(l) for l in ledgers]

@router.get("/ledgers/{ledger_id}", response_model=Ledger)
async def get_ledger(ledger_id: str, current_user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(DBLedger).where(DBLedger.id == ledger_id))
    ledger = result.scalar_one_or_none()
    if not ledger:
        raise HTTPException(status_code=404, detail="Ledger not found")
    return to_dict(ledger)

@router.put("/ledgers/{ledger_id}", response_model=Ledger)
async def update_ledger(ledger_id: str, ledger: LedgerCreate, current_user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(DBLedger).where(DBLedger.id == ledger_id))
    existing = result.scalar_one_or_none()
    if not existing:
        raise HTTPException(status_code=404, detail="Ledger not found")
    
    # Validate account group
    res_group = await session.execute(select(DBAccountGroup).where(DBAccountGroup.id == ledger.account_group_id))
    group = res_group.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Account group not found")
    
    update_data = ledger.model_dump(exclude={"opening_balance"})  # Don't update opening balance
    for key, value in update_data.items():
        setattr(existing, key, value)
    
    await session.commit()
    return to_dict(existing)

@router.delete("/ledgers/{ledger_id}")
async def delete_ledger(ledger_id: str, current_user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    # PostgreSQL handle karega proper migration hone pe
    result = await session.execute(select(DBLedger).where(DBLedger.id == ledger_id))
    ledger = result.scalar_one_or_none()
    
    if not ledger:
        raise HTTPException(status_code=404, detail="Ledger not found")
    
    ledger.is_active = False
    await session.commit()
    return {"message": "Ledger deleted successfully"}

# ==================== BRANCHES ====================

@router.post("/branches", response_model=Branch)
async def create_branch(branch: BranchCreate, current_user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    # Check if code exists
    res = await session.execute(select(DBBranch).where(DBBranch.code == branch.code))
    existing = res.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Branch code already exists")
    
    new_branch = DBBranch(id=str(uuid.uuid4()), **branch.model_dump(), is_active=True, created_at=datetime.now(timezone.utc))
    session.add(new_branch)
    await session.commit()
    return to_dict(new_branch)

@router.get("/branches", response_model=List[Branch])
async def get_branches(current_user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(DBBranch).where(DBBranch.is_active == True))
    branches = result.scalars().all()
    return [to_dict(b) for b in branches]

@router.put("/branches/{branch_id}")
async def update_branch(branch_id: str, branch: BranchCreate, current_user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(DBBranch).where(DBBranch.id == branch_id))
    existing = result.scalar_one_or_none()
    if not existing:
        raise HTTPException(status_code=404, detail="Branch not found")
    
    for key, val in branch.model_dump().items():
        setattr(existing, key, val)
    await session.commit()
    return {"message": "Branch updated successfully"}

# ==================== GODOWNS ====================

@router.post("/godowns", response_model=Godown)
async def create_godown(godown: GodownCreate, current_user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    # Validate branch
    res = await session.execute(select(DBBranch).where(DBBranch.id == godown.branch_id))
    branch = res.scalar_one_or_none()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    
    new_godown = DBGodown(id=str(uuid.uuid4()), **godown.model_dump(), is_active=True, created_at=datetime.now(timezone.utc))
    session.add(new_godown)
    await session.commit()
    return to_dict(new_godown)

@router.get("/godowns", response_model=List[Godown])
async def get_godowns(branch_id: str = None, current_user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    query = select(DBGodown).where(DBGodown.is_active == True)
    if branch_id:
        query = query.where(DBGodown.branch_id == branch_id)
    
    result = await session.execute(query)
    godowns = result.scalars().all()
    return [to_dict(g) for g in godowns]
