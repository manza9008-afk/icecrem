from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from models_accounting import *
from utils import get_current_user
from datetime import datetime, timezone
import uuid

router = APIRouter(prefix="/api/accounting", tags=["vouchers"])

from server import db

# ==================== VOUCHER ENTRY ====================

async def get_next_voucher_number(voucher_type: str, branch_id: str = None) -> str:
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
        branch = await db.branches.find_one({"id": branch_id})
        if branch:
            branch_code = f"{branch['code']}/"
    
    # Get last voucher number
    query = {"voucher_type": voucher_type}
    if branch_id:
        query["branch_id"] = branch_id
    
    last_voucher = await db.vouchers.find_one(
        query,
        sort=[("created_at", -1)]
    )
    
    if last_voucher and "voucher_number" in last_voucher:
        # Extract number from last voucher
        parts = last_voucher["voucher_number"].split("/")
        last_num = int(parts[-1])
        new_num = last_num + 1
    else:
        new_num = 1
    
    return f"{prefix}/{branch_code}2025-26/{new_num:05d}"

async def post_to_ledger(db, voucher_id: str, voucher_number: str, voucher_date: str, entries: List[VoucherEntryItem]):
    """Post voucher entries to ledgers"""
    for entry in entries:
        ledger = await db.ledgers.find_one({"id": entry.ledger_id})
        if not ledger:
            continue
        
        # Calculate balance change
        amount = entry.amount
        if entry.entry_type == "debit":
            balance_change = amount
        else:  # credit
            balance_change = -amount
        
        # Update ledger balance
        new_balance = ledger["current_balance"] + balance_change
        await db.ledgers.update_one(
            {"id": entry.ledger_id},
            {"$set": {"current_balance": new_balance}}
        )
        
        # Create ledger transaction entry
        ledger_transaction = {
            "id": str(uuid.uuid4()),
            "ledger_id": entry.ledger_id,
            "voucher_id": voucher_id,
            "voucher_number": voucher_number,
            "voucher_date": voucher_date,
            "entry_type": entry.entry_type,
            "amount": amount,
            "balance": new_balance,
            "narration": entry.narration,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.ledger_transactions.insert_one(ledger_transaction)

async def reverse_ledger_posting(db, voucher_id: str):
    """Reverse ledger entries for a voucher"""
    # Find all ledger transactions for this voucher
    transactions = await db.ledger_transactions.find({"voucher_id": voucher_id}).to_list(100)
    
    for trans in transactions:
        ledger = await db.ledgers.find_one({"id": trans["ledger_id"]})
        if not ledger:
            continue
        
        # Reverse the balance change
        if trans["entry_type"] == "debit":
            balance_change = -trans["amount"]
        else:
            balance_change = trans["amount"]
        
        new_balance = ledger["current_balance"] + balance_change
        await db.ledgers.update_one(
            {"id": trans["ledger_id"]},
            {"$set": {"current_balance": new_balance}}
        )
    
    # Delete ledger transaction entries
    await db.ledger_transactions.delete_many({"voucher_id": voucher_id})

@router.post("/vouchers", response_model=Voucher)
async def create_voucher(voucher: VoucherCreate, current_user: dict = Depends(get_current_user)):
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
        ledger = await db.ledgers.find_one({"id": entry.ledger_id})
        if not ledger:
            raise HTTPException(status_code=404, detail=f"Ledger {entry.ledger_name} not found")
    
    # Generate voucher number
    voucher_number = await get_next_voucher_number(voucher.voucher_type, voucher.branch_id)
    
    # Create voucher
    voucher_obj = Voucher(
        **voucher.model_dump(),
        voucher_number=voucher_number,
        total_amount=debit_total,
        created_by=current_user["username"]
    )
    
    doc = voucher_obj.model_dump()
    await db.vouchers.insert_one(doc)
    
    # Post to ledgers
    await post_to_ledger(db, voucher_obj.id, voucher_number, voucher.voucher_date, voucher.entries)
    
    return voucher_obj

@router.get("/vouchers", response_model=List[Voucher])
async def get_vouchers(
    voucher_type: Optional[str] = None,
    branch_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    query = {}
    if voucher_type:
        query["voucher_type"] = voucher_type
    if branch_id:
        query["branch_id"] = branch_id
    if start_date:
        query["voucher_date"] = {"$gte": start_date}
    if end_date:
        if "voucher_date" in query:
            query["voucher_date"]["$lte"] = end_date
        else:
            query["voucher_date"] = {"$lte": end_date}
    
    vouchers = await db.vouchers.find(query, {"_id": 0}).sort("voucher_date", -1).to_list(1000)
    return vouchers

@router.get("/vouchers/{voucher_id}", response_model=Voucher)
async def get_voucher(voucher_id: str, current_user: dict = Depends(get_current_user)):
    voucher = await db.vouchers.find_one({"id": voucher_id}, {"_id": 0})
    if not voucher:
        raise HTTPException(status_code=404, detail="Voucher not found")
    return voucher

@router.put("/vouchers/{voucher_id}", response_model=Voucher)
async def update_voucher(voucher_id: str, voucher: VoucherCreate, current_user: dict = Depends(get_current_user)):
    """Update voucher with reverse and re-post"""
    existing = await db.vouchers.find_one({"id": voucher_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Voucher not found")
    
    # Validate new entries
    debit_total = sum(e.amount for e in voucher.entries if e.entry_type == "debit")
    credit_total = sum(e.amount for e in voucher.entries if e.entry_type == "credit")
    
    if abs(debit_total - credit_total) > 0.01:
        raise HTTPException(status_code=400, detail="Voucher not balanced")
    
    # Reverse old posting
    await reverse_ledger_posting(db, voucher_id)
    
    # Update voucher
    update_data = voucher.model_dump()
    update_data["total_amount"] = debit_total
    update_data["modified_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.vouchers.update_one({"id": voucher_id}, {"$set": update_data})
    
    # Re-post to ledgers
    await post_to_ledger(db, voucher_id, existing["voucher_number"], voucher.voucher_date, voucher.entries)
    
    updated = await db.vouchers.find_one({"id": voucher_id}, {"_id": 0})
    return updated

@router.delete("/vouchers/{voucher_id}")
async def delete_voucher(voucher_id: str, current_user: dict = Depends(get_current_user)):
    """Delete voucher with complete reversal"""
    existing = await db.vouchers.find_one({"id": voucher_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Voucher not found")
    
    # Reverse ledger posting
    await reverse_ledger_posting(db, voucher_id)
    
    # Delete voucher
    await db.vouchers.delete_one({"id": voucher_id})
    
    return {"message": "Voucher deleted and ledgers reversed"}

# ==================== LEDGER REPORTS ====================

@router.get("/ledgers/{ledger_id}/statement")
async def get_ledger_statement(
    ledger_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get ledger statement with running balance"""
    ledger = await db.ledgers.find_one({"id": ledger_id}, {"_id": 0})
    if not ledger:
        raise HTTPException(status_code=404, detail="Ledger not found")
    
    query = {"ledger_id": ledger_id}
    if start_date:
        query["voucher_date"] = {"$gte": start_date}
    if end_date:
        if "voucher_date" in query:
            query["voucher_date"]["$lte"] = end_date
        else:
            query["voucher_date"] = {"$lte": end_date}
    
    transactions = await db.ledger_transactions.find(
        query, {"_id": 0}
    ).sort("voucher_date", 1).to_list(10000)
    
    return {
        "ledger": ledger,
        "opening_balance": ledger["opening_balance"],
        "transactions": transactions,
        "closing_balance": ledger["current_balance"]
    }

@router.get("/reports/day-book")
async def get_day_book(
    start_date: str,
    end_date: str,
    branch_id: Optional[str] = None,
    voucher_type: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get day book (all vouchers with details)"""
    query = {
        "voucher_date": {"$gte": start_date, "$lte": end_date}
    }
    if branch_id:
        query["branch_id"] = branch_id
    if voucher_type:
        query["voucher_type"] = voucher_type
    
    vouchers = await db.vouchers.find(query, {"_id": 0}).sort("voucher_date", 1).to_list(10000)
    
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
    current_user: dict = Depends(get_current_user)
):
    """Get trial balance (must always balance)"""
    query = {"is_active": True}
    if branch_id:
        query["branch_id"] = branch_id
    
    ledgers = await db.ledgers.find(query, {"_id": 0}).to_list(10000)
    
    # Get account groups for grouping
    groups = await db.account_groups.find({}, {"_id": 0}).to_list(1000)
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
    current_user: dict = Depends(get_current_user)
):
    """Generate Profit & Loss Statement"""
    # Get all income and expense ledgers
    income_groups = await db.account_groups.find({"account_type": "Income"}, {"_id": 0}).to_list(100)
    expense_groups = await db.account_groups.find({"account_type": "Expense"}, {"_id": 0}).to_list(100)
    
    income_group_ids = [g["id"] for g in income_groups]
    expense_group_ids = [g["id"] for g in expense_groups]
    
    query = {"is_active": True}
    if branch_id:
        query["branch_id"] = branch_id
    
    all_ledgers = await db.ledgers.find(query, {"_id": 0}).to_list(10000)
    
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
    current_user: dict = Depends(get_current_user)
):
    """Generate Balance Sheet"""
    # Get P&L for net profit
    pl = await get_profit_loss("2025-04-01", end_date, branch_id, current_user)
    net_profit = pl["net_profit"]
    
    # Get all asset, liability, capital ledgers
    asset_groups = await db.account_groups.find({"account_type": "Asset"}, {"_id": 0}).to_list(100)
    liability_groups = await db.account_groups.find({"account_type": "Liability"}, {"_id": 0}).to_list(100)
    capital_groups = await db.account_groups.find({"account_type": "Capital"}, {"_id": 0}).to_list(100)
    
    asset_group_ids = [g["id"] for g in asset_groups]
    liability_group_ids = [g["id"] for g in liability_groups]
    capital_group_ids = [g["id"] for g in capital_groups]
    
    query = {"is_active": True}
    if branch_id:
        query["branch_id"] = branch_id
    
    all_ledgers = await db.ledgers.find(query, {"_id": 0}).to_list(10000)
    
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
