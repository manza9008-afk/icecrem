"""
HOOREN ERP - Branch & Godown Routes
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime, timezone
import uuid

router = APIRouter(prefix="/api/branches", tags=["branches"])

from database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from db_models import Branch as DBBranch, Godown as DBGodown
from utils import get_current_user

def to_dict(obj):
    if not obj: return {}
    result = {}
    for c in obj.__table__.columns:
        val = getattr(obj, c.name)
        if hasattr(val, 'isoformat'):
            val = val.isoformat()
        result[c.name] = val
    return result

STOCK_LOCATIONS = [
    {"code_suffix": "STORE", "name": "Store", "is_default": True},
    {"code_suffix": "COLD", "name": "Cold Room", "is_default": False},
]

async def ensure_stock_locations(session: AsyncSession, branch_id: str, branch_code: str = "", address: str = ""):
    """Keep stock dropdown limited to Store and Cold Room without losing old stock."""
    res = await session.execute(select(DBGodown).where(DBGodown.branch_id == branch_id).where(DBGodown.is_active == True))
    godowns = res.scalars().all()
    
    legacy = next((g for g in godowns if g.name in ["Maza", "Main Godown", "Main Store"]), None)
    store = next((g for g in godowns if g.name == "Store"), None)

    if not store and legacy:
        legacy.name = "Store"
        legacy.code = legacy.code or f"{branch_code}-STORE"
        legacy.is_default = True
    elif store:
        store.is_default = True

    for location in STOCK_LOCATIONS:
        exists = next((g for g in godowns if g.name == location["name"]), None)
        if exists:
            continue

        code_prefix = branch_code or "STK"
        new_godown = DBGodown(
            id=str(uuid.uuid4()),
            code=f"{code_prefix}-{location['code_suffix']}",
            name=location["name"],
            branch_id=branch_id,
            address=address,
            is_default=location["is_default"],
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        session.add(new_godown)
        godowns.append(new_godown)

    await session.commit()
    order = {location["name"]: index for index, location in enumerate(STOCK_LOCATIONS)}
    sorted_godowns = sorted(godowns, key=lambda g: order.get(g.name, 99))
    return [to_dict(g) for g in sorted_godowns]

@router.post("")
async def create_branch(branch_data: dict, current_user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    """Create a new branch"""
    res = await session.execute(select(DBBranch).where(DBBranch.code == branch_data["code"]))
    existing = res.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Branch code already exists")
    
    new_branch = DBBranch(id=str(uuid.uuid4()), **branch_data, is_active=True, created_at=datetime.now(timezone.utc))
    session.add(new_branch)
    await session.commit()
    
    await ensure_stock_locations(session, new_branch.id, branch_data.get("code", ""), branch_data.get("address", ""))
    return to_dict(new_branch)


@router.get("", response_model=List[dict])
async def get_branches(
    is_active: bool = True,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Get all branches"""
    query = select(DBBranch)
    if is_active is not None:
        query = query.where(DBBranch.is_active == is_active)
    res = await session.execute(query)
    return [to_dict(b) for b in res.scalars().all()]


@router.get("/{branch_id}")
async def get_branch(branch_id: str, current_user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    """Get branch by ID"""
    res = await session.execute(select(DBBranch).where(DBBranch.id == branch_id))
    branch = res.scalar_one_or_none()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    return to_dict(branch)


@router.put("/{branch_id}")
async def update_branch(
    branch_id: str,
    branch_data: dict,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Update branch"""
    res = await session.execute(select(DBBranch).where(DBBranch.id == branch_id))
    existing = res.scalar_one_or_none()
    if not existing:
        raise HTTPException(status_code=404, detail="Branch not found")
    
    # Check code uniqueness
    if "code" in branch_data:
        res_code = await session.execute(select(DBBranch).where(DBBranch.code == branch_data["code"]).where(DBBranch.id != branch_id))
        if res_code.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Branch code already exists")
    
    for k, v in branch_data.items():
        setattr(existing, k, v)
    await session.commit()
    
    return {"message": "Branch updated successfully"}


@router.delete("/{branch_id}")
async def delete_branch(branch_id: str, current_user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    """Soft delete branch"""
    res = await session.execute(select(DBBranch).where(DBBranch.id == branch_id))
    existing = res.scalar_one_or_none()
    if not existing:
        raise HTTPException(status_code=404, detail="Branch not found")
    
    existing.is_active = False
    await session.commit()
    
    return {"message": "Branch deleted successfully"}


# ==================== GODOWNS ====================

@router.post("/{branch_id}/godowns")
async def create_godown(
    branch_id: str,
    godown_data: dict,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Create a godown for a branch"""
    res_b = await session.execute(select(DBBranch).where(DBBranch.id == branch_id))
    if not res_b.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Branch not found")
    
    new_g = DBGodown(id=str(uuid.uuid4()), branch_id=branch_id, **godown_data, is_active=True, created_at=datetime.now(timezone.utc))
    session.add(new_g)
    await session.commit()
    return to_dict(new_g)


@router.get("/{branch_id}/godowns")
async def get_godowns(
    branch_id: str,
    is_active: bool = True,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Get godowns for a branch"""
    res_b = await session.execute(select(DBBranch).where(DBBranch.id == branch_id))
    branch = res_b.scalar_one_or_none()
    
    if is_active and branch:
        return await ensure_stock_locations(session, branch_id, getattr(branch, "code", ""), getattr(branch, "address", ""))
        
    query = select(DBGodown).where(DBGodown.branch_id == branch_id)
    if is_active is not None:
        query = query.where(DBGodown.is_active == is_active)
    
    res = await session.execute(query)
    return [to_dict(g) for g in res.scalars().all()]


@router.get("/godowns/all")
async def get_all_godowns(
    is_active: bool = True,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Get all godowns across branches"""
    query = select(DBGodown)
    if is_active is not None:
        query = query.where(DBGodown.is_active == is_active)
    
    res = await session.execute(query)
    godowns = res.scalars().all()
    result = []
    for g in godowns:
        gd = to_dict(g)
        res_b = await session.execute(select(DBBranch).where(DBBranch.id == g.branch_id))
        b = res_b.scalar_one_or_none()
        gd["branch_name"] = getattr(b, "name", "Unknown")
        result.append(gd)
    
    return result


@router.put("/godowns/{godown_id}")
async def update_godown(
    godown_id: str,
    godown_data: dict,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Update godown"""
    res = await session.execute(select(DBGodown).where(DBGodown.id == godown_id))
    existing = res.scalar_one_or_none()
    if not existing:
        raise HTTPException(status_code=404, detail="Godown not found")
    
    for k, v in godown_data.items():
        setattr(existing, k, v)
    await session.commit()
    
    return {"message": "Godown updated successfully"}


@router.delete("/godowns/{godown_id}")
async def delete_godown(godown_id: str, current_user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    """Soft delete godown"""
    res = await session.execute(select(DBGodown).where(DBGodown.id == godown_id))
    existing = res.scalar_one_or_none()
    if not existing:
        raise HTTPException(status_code=404, detail="Godown not found")
    
    existing.is_active = False
    await session.commit()
    
    return {"message": "Godown deleted successfully"}