from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from models_accounting import *
from utils import get_current_user
from datetime import datetime, timezone
import uuid
import json

router = APIRouter(prefix="/api/accounting", tags=["vouchers"])

from database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc
from db_models import Voucher as DBVoucher, Ledger as DBLedger, LedgerTransaction as DBLedgerTransaction, Branch as DBBranch, AccountGroup as DBAccountGroup

def to_dict(obj):
    if not obj: return {}
    d = {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
    if 'entries' in d and isinstance(d['entries'], str):
        try: d['entries'] = json.loads(d['entries'])
        except: pass
    return d

# ==================== VOUCHER ENTRY ====================

async def get_next_voucher_number(session: AsyncSession, voucher_type: str, branch_id: str = None) -> str:
    """Generate next voucher number for given type"""
    prefix_map = {
        "journal": "JV",
        "payment": "PV",
        "receipt": "RV",
        "contra": "CV",
        "debit_note": "DN",
        "credit_note": "CN"
    }
    
    prefix = prefix_map.get(voucher_type, "VC")
    branch_code = ""
    
    if branch_id:
        res = await session.execute(select(DBBranch).where(DBBranch.id == branch_id))
        branch = res.scalar_one_or_none()
        if branch:
            branch_code = f"{branch.code}/"
    
    # Get last voucher number
    query = select(DBVoucher).where(DBVoucher.voucher_type == voucher_type)
    if branch_id:
        query = query.where(DBVoucher.branch_id == branch_id)
    
    query = query.order_by(desc(DBVoucher.created_at)).limit(1)
    res = await session.execute(query)
    last_voucher = res.scalar_one_or_none()
    
    if last_voucher and last_voucher.voucher_number:
        # Extract number from last voucher
        parts = last_voucher.voucher_number.split("/")
        last_num = int(parts[-1])
        new_num = last_num + 1
    else:
        new_num = 1
    
    return f"{prefix}/{branch_code}2025-26/{new_num:05d}"

async def post_to_ledger(session: AsyncSession, voucher_id: str, voucher_number: str, voucher_date: str, entries: List[VoucherEntryItem]):
    """Post voucher entries to ledgers"""
    for entry in entries:
        res = await session.execute(select(DBLedger).where(DBLedger.id == entry.ledger_id))
        ledger = res.scalar_one_or_none()
        if not ledger:
            continue
        
        # Calculate balance change
        amount = entry.amount
        if entry.entry_type == "debit":
            balance_change = amount
        else:  # credit
            balance_change = -amount
        
        # Update ledger balance
        new_balance = ledger.current_balance + balance_change
        ledger.current_balance = new_balance
        
        # Create ledger transaction entry
        ledger_transaction = DBLedgerTransaction(
            id=str(uuid.uuid4()),
            ledger_id=entry.ledger_id,
            voucher_id=voucher_id,
            voucher_number=voucher_number,
            voucher_date=voucher_date,
            entry_type=entry.entry_type,
            amount=amount,
            balance=new_balance,
            narration=entry.narration,
            created_at=datetime.now(timezone.utc)
        )
        session.add(ledger_transaction)

async def reverse_ledger_posting(session: AsyncSession, voucher_id: str):
    """Reverse ledger entries for a voucher"""
    res = await session.execute(select(DBLedgerTransaction).where(DBLedgerTransaction.voucher_id == voucher_id))
    transactions = res.scalars().all()
    
    for trans in transactions:
        res_l = await session.execute(select(DBLedger).where(DBLedger.id == trans.ledger_id))
        ledger = res_l.scalar_one_or_none()
        if not ledger:
            continue
        
        # Reverse the balance change
        if trans.entry_type == "debit":
            balance_change = -trans.amount
        else:
            balance_change = trans.amount
        
        ledger.current_balance = ledger.current_balance + balance_change
    
    # Delete ledger transaction entries
    for trans in transactions:
        await session.delete(trans)

@router.post("/vouchers", response_model=Voucher)
async def create_voucher(voucher: VoucherCreate, current_user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    """Create a new voucher with double-entry validation"""
    
    # Validate entries
    if not voucher.entries or len(voucher.entries) == 0:
        raise HTTPException(status_code=400, detail="Voucher must have at least one entry")
    
    # Calculate Dr/Cr totals
    debit_total = sum(e.amount for e in voucher.entries if e.entry_type == "debit")
    credit_total = sum(e.amount for e in voucher.entries if e.entry_type == "credit")
    
    if abs(debit_total - credit_total) > 0.01:  # Allow 1 paisa difference for rounding
        raise HTTPException(
            status_code=400, 
            detail=f"Voucher not balanced. Dr: {debit_total}, Cr: {credit_total}"
        )
    
    # Validate all ledgers exist
    for entry in voucher.entries:
        res = await session.execute(select(DBLedger).where(DBLedger.id == entry.ledger_id))
        ledger = res.scalar_one_or_none()
        if not ledger:
            raise HTTPException(status_code=404, detail=f"Ledger {entry.ledger_name} not found")
    
    # Generate voucher number
    voucher_number = await get_next_voucher_number(session, voucher.voucher_type, voucher.branch_id)
    
    # Create voucher
    new_voucher = DBVoucher(
        id=str(uuid.uuid4()),
        voucher_number=voucher_number,
        voucher_type=voucher.voucher_type,
        voucher_date=voucher.voucher_date,
        branch_id=voucher.branch_id,
        narration=voucher.narration,
        reference_number=voucher.reference_number,
        total_debit=debit_total,
        total_credit=credit_total,
        status="approved",
        entries=json.dumps([e.model_dump() for e in voucher.entries]),
        created_by=current_user["username"],
        created_at=datetime.now(timezone.utc)
    )
    session.add(new_voucher)
    
    # Post to ledgers
    await post_to_ledger(session, new_voucher.id, voucher_number, voucher.voucher_date, voucher.entries)
    await session.commit()
    
    return to_dict(new_voucher)

@router.get("/vouchers", response_model=List[Voucher])
async def get_vouchers(
    voucher_type: Optional[str] = None,
    branch_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    query = select(DBVoucher)
    if voucher_type:
        query = query.where(DBVoucher.voucher_type == voucher_type)
    if branch_id:
        query = query.where(DBVoucher.branch_id == branch_id)
    if start_date:
        query = query.where(DBVoucher.voucher_date >= start_date)
    if end_date:
        query = query.where(DBVoucher.voucher_date <= end_date)
    
    query = query.order_by(desc(DBVoucher.voucher_date))
    res = await session.execute(query)
    return [to_dict(v) for v in res.scalars().all()]

@router.get("/vouchers/{voucher_id}", response_model=Voucher)
async def get_voucher(voucher_id: str, current_user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    res = await session.execute(select(DBVoucher).where(DBVoucher.id == voucher_id))
    voucher = res.scalar_one_or_none()
    if not voucher:
        raise HTTPException(status_code=404, detail="Voucher not found")
    return to_dict(voucher)

@router.put("/vouchers/{voucher_id}", response_model=Voucher)
async def update_voucher(voucher_id: str, voucher: VoucherCreate, current_user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    """Update voucher with reverse and re-post"""
    res = await session.execute(select(DBVoucher).where(DBVoucher.id == voucher_id))
    existing = res.scalar_one_or_none()
    if not existing:
        raise HTTPException(status_code=404, detail="Voucher not found")
    
    # Validate new entries
    debit_total = sum(e.amount for e in voucher.entries if e.entry_type == "debit")
    credit_total = sum(e.amount for e in voucher.entries if e.entry_type == "credit")
    
    if abs(debit_total - credit_total) > 0.01:
        raise HTTPException(status_code=400, detail="Voucher not balanced")
    
    # Reverse old posting
    await reverse_ledger_posting(session, voucher_id)
    
    # Update voucher
    existing.voucher_type = voucher.voucher_type
    existing.voucher_date = voucher.voucher_date
    existing.narration = voucher.narration
    existing.reference_number = voucher.reference_number
    existing.entries = json.dumps([e.model_dump() for e in voucher.entries])
    existing.total_debit = debit_total
    existing.total_credit = credit_total
    existing.modified_at = datetime.now(timezone.utc).isoformat()
    
    # Re-post to ledgers
    await post_to_ledger(session, voucher_id, existing.voucher_number, voucher.voucher_date, voucher.entries)
    await session.commit()
    
    return to_dict(existing)

@router.delete("/vouchers/{voucher_id}")
async def delete_voucher(voucher_id: str, current_user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    """Delete voucher with complete reversal"""
    res = await session.execute(select(DBVoucher).where(DBVoucher.id == voucher_id))
    existing = res.scalar_one_or_none()
    if not existing:
        raise HTTPException(status_code=404, detail="Voucher not found")
    
    # Reverse ledger posting
    await reverse_ledger_posting(session, voucher_id)
    
    # Delete voucher
    await session.delete(existing)
    await session.commit()
    
    return {"message": "Voucher deleted and ledgers reversed"}

# ==================== LEDGER REPORTS ====================

@router.get("/ledgers/{ledger_id}/statement")
async def get_ledger_statement(
    ledger_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Get ledger statement with running balance"""
    res = await session.execute(select(DBLedger).where(DBLedger.id == ledger_id))
    ledger = res.scalar_one_or_none()
    if not ledger:
        raise HTTPException(status_code=404, detail="Ledger not found")
    
    query = select(DBLedgerTransaction).where(DBLedgerTransaction.ledger_id == ledger_id)
    if start_date:
        query = query.where(DBLedgerTransaction.voucher_date >= start_date)
    if end_date:
        query = query.where(DBLedgerTransaction.voucher_date <= end_date)
    
    query = query.order_by(DBLedgerTransaction.voucher_date)
    res_trans = await session.execute(query)
    transactions = res_trans.scalars().all()
    
    return {
        "ledger": to_dict(ledger),
        "opening_balance": ledger.opening_balance,
        "transactions": [to_dict(t) for t in transactions],
        "closing_balance": ledger.current_balance
    }

@router.get("/reports/day-book")
async def get_day_book(
    start_date: str,
    end_date: str,
    branch_id: Optional[str] = None,
    voucher_type: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Get day book (all vouchers with details)"""
    query = select(DBVoucher).where(DBVoucher.voucher_date >= start_date).where(DBVoucher.voucher_date <= end_date)
    if branch_id:
        query = query.where(DBVoucher.branch_id == branch_id)
    if voucher_type:
        query = query.where(DBVoucher.voucher_type == voucher_type)
    
    query = query.order_by(DBVoucher.voucher_date)
    res = await session.execute(query)
    vouchers = [to_dict(v) for v in res.scalars().all()]
    
    return {
        "start_date": start_date,
        "end_date": end_date,
        "vouchers": vouchers,
        "total_vouchers": len(vouchers)
    }

@router.get("/reports/trial-balance")
async def get_trial_balance(
    end_date: Optional[str] = None,
    branch_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Get trial balance (must always balance)"""
    query = select(DBLedger).where(DBLedger.is_active == True)
    if branch_id:
        query = query.where(DBLedger.branch_id == branch_id)
    
    res = await session.execute(query)
    ledgers = [to_dict(l) for l in res.scalars().all()]
    
    # Get account groups for grouping
    res_groups = await session.execute(select(DBAccountGroup))
    groups = [to_dict(g) for g in res_groups.scalars().all()]
    groups_dict = {g["id"]: g for g in groups}
    
    trial_balance_data = []
    total_debit = 0
    total_credit = 0
    
    for ledger in ledgers:
        balance = ledger["current_balance"]
        group = groups_dict.get(ledger["account_group_id"], {})
        
        if balance >= 0:
            debit_balance = balance
            credit_balance = 0
        else:
            debit_balance = 0
            credit_balance = abs(balance)
        
        total_debit += debit_balance
        total_credit += credit_balance
        
        trial_balance_data.append({
            "ledger_id": ledger["id"],
            "ledger_name": ledger["name"],
            "group_name": group.get("name", "Unknown"),
            "account_type": group.get("account_type", "Unknown"),
            "debit": debit_balance,
            "credit": credit_balance
        })
    
    # Sort by account type then ledger name
    trial_balance_data.sort(key=lambda x: (x["account_type"], x["ledger_name"]))
    
    return {
        "as_on_date": end_date or datetime.now(timezone.utc).isoformat()[:10],
        "ledgers": trial_balance_data,
        "total_debit": total_debit,
        "total_credit": total_credit,
        "difference": abs(total_debit - total_credit),
        "is_balanced": abs(total_debit - total_credit) < 0.01
    }

@router.get("/reports/profit-loss")
async def get_profit_loss(
    start_date: str,
    end_date: str,
    branch_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Generate Profit & Loss Statement"""
    # Get all income and expense ledgers
    res_inc = await session.execute(select(DBAccountGroup).where(DBAccountGroup.account_type == "Income"))
    res_exp = await session.execute(select(DBAccountGroup).where(DBAccountGroup.account_type == "Expense"))
    
    income_group_ids = [g.id for g in res_inc.scalars().all()]
    expense_group_ids = [g.id for g in res_exp.scalars().all()]
    
    query = select(DBLedger).where(DBLedger.is_active == True)
    if branch_id:
        query = query.where(DBLedger.branch_id == branch_id)
    
    res_all = await session.execute(query)
    all_ledgers = [to_dict(l) for l in res_all.scalars().all()]
    
    income_ledgers = [l for l in all_ledgers if l["account_group_id"] in income_group_ids]
    expense_ledgers = [l for l in all_ledgers if l["account_group_id"] in expense_group_ids]
    
    total_income = sum(abs(l["current_balance"]) for l in income_ledgers)
    total_expense = sum(abs(l["current_balance"]) for l in expense_ledgers)
    
    net_profit = total_income - total_expense
    
    return {
        "period": {"start_date": start_date, "end_date": end_date},
        "income": [
            {"ledger_name": l["name"], "amount": abs(l["current_balance"])}
            for l in income_ledgers
        ],
        "expenses": [
            {"ledger_name": l["name"], "amount": abs(l["current_balance"])}
            for l in expense_ledgers
        ],
        "total_income": total_income,
        "total_expense": total_expense,
        "net_profit": net_profit
    }

@router.get("/reports/balance-sheet")
async def get_balance_sheet(
    end_date: str,
    branch_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Generate Balance Sheet"""
    # Get P&L for net profit
    pl = await get_profit_loss("2025-04-01", end_date, branch_id, current_user, session)
    net_profit = pl["net_profit"]
    
    # Get all asset, liability, capital ledgers
    res_groups = await session.execute(select(DBAccountGroup))
    groups = res_groups.scalars().all()
    
    asset_group_ids = [g.id for g in groups if g.account_type == "Asset"]
    liability_group_ids = [g.id for g in groups if g.account_type == "Liability"]
    capital_group_ids = [g.id for g in groups if g.account_type == "Capital"]
    
    query = select(DBLedger).where(DBLedger.is_active == True)
    if branch_id:
        query = query.where(DBLedger.branch_id == branch_id)
    
    res_all = await session.execute(query)
    all_ledgers = [to_dict(l) for l in res_all.scalars().all()]
    
    asset_ledgers = [l for l in all_ledgers if l["account_group_id"] in asset_group_ids]
    liability_ledgers = [l for l in all_ledgers if l["account_group_id"] in liability_group_ids]
    capital_ledgers = [l for l in all_ledgers if l["account_group_id"] in capital_group_ids]
    
    total_assets = sum(l["current_balance"] for l in asset_ledgers)
    total_liabilities = sum(abs(l["current_balance"]) for l in liability_ledgers)
    total_capital = sum(abs(l["current_balance"]) for l in capital_ledgers)
    
    return {
        "as_on_date": end_date,
        "assets": [
            {"ledger_name": l["name"], "amount": l["current_balance"]}
            for l in asset_ledgers
        ],
        "liabilities": [
            {"ledger_name": l["name"], "amount": abs(l["current_balance"])}
            for l in liability_ledgers
        ],
        "capital": [
            {"ledger_name": l["name"], "amount": abs(l["current_balance"])}
            for l in capital_ledgers
        ],
        "net_profit": net_profit,
        "total_assets": total_assets,
        "total_liabilities_and_capital": total_liabilities + total_capital + net_profit
    }
