"""
HOOREN ERP - Core Accounting Routes
Account Groups, Ledgers, Vouchers
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime, timezone
import uuid

router = APIRouter(prefix="/api/accounting", tags=["accounting"])

from server import db
from utils import get_current_user
from services.accounting_service import (
    seed_chart_of_accounts,
    post_to_ledgers,
    reverse_ledger_postings,
    get_next_voucher_number,
    create_reversal_voucher,
    calculate_trial_balance,
    calculate_profit_loss,
    calculate_balance_sheet
)


# ==================== SETUP ====================

@router.post("/setup/seed-chart-of-accounts")
async def seed_coa(branch_id: str, current_user: dict = Depends(get_current_user)):
    """Seed standard Indian Chart of Accounts"""
    result = await seed_chart_of_accounts(db, branch_id)
    return result


# ==================== ACCOUNT GROUPS ====================

@router.get("/account-groups")
async def get_account_groups(
    account_type: Optional[str] = None,
    parent_id: Optional[str] = None,
    is_active: bool = True,
    current_user: dict = Depends(get_current_user)
):
    """Get all account groups"""
    query = {}
    if is_active is not None:
        query["is_active"] = is_active
    if account_type:
        query["account_type"] = account_type
    if parent_id:
        query["parent_id"] = parent_id
    
    groups = await db.account_groups.find(query, {"_id": 0}).to_list(1000)
    return groups


@router.get("/account-groups/tree")
async def get_account_groups_tree(current_user: dict = Depends(get_current_user)):
    """Get account groups in hierarchical tree structure"""
    all_groups = await db.account_groups.find({"is_active": True}, {"_id": 0}).to_list(1000)
    
    # Build tree
    groups_dict = {g['id']: {**g, 'children': [], 'level': 0} for g in all_groups}
    tree = []
    
    def calculate_level(group_id, level=0):
        if group_id in groups_dict:
            groups_dict[group_id]['level'] = level
            for child_id, child in groups_dict.items():
                if child.get('parent_id') == group_id:
                    calculate_level(child_id, level + 1)
    
    for group in all_groups:
        if group.get('parent_id'):
            parent = groups_dict.get(group['parent_id'])
            if parent:
                parent['children'].append(groups_dict[group['id']])
        else:
            tree.append(groups_dict[group['id']])
            calculate_level(group['id'])
    
    return tree


@router.post("/account-groups")
async def create_account_group(
    group_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Create a new account group"""
    # Check code uniqueness
    existing = await db.account_groups.find_one({"code": group_data["code"]})
    if existing:
        raise HTTPException(status_code=400, detail="Account group code already exists")
    
    # Validate parent
    if group_data.get("parent_id"):
        parent = await db.account_groups.find_one({"id": group_data["parent_id"]})
        if not parent:
            raise HTTPException(status_code=404, detail="Parent group not found")
    
    group_doc = {
        "id": str(uuid.uuid4()),
        **group_data,
        "is_system": False,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.account_groups.insert_one(group_doc)
    group_doc.pop("_id", None)
    return group_doc


@router.put("/account-groups/{group_id}")
async def update_account_group(
    group_id: str,
    group_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Update account group"""
    existing = await db.account_groups.find_one({"id": group_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Account group not found")
    
    if existing.get("is_system"):
        raise HTTPException(status_code=400, detail="Cannot modify system account group")
    
    await db.account_groups.update_one({"id": group_id}, {"$set": group_data})
    return {"message": "Account group updated"}


@router.delete("/account-groups/{group_id}")
async def delete_account_group(group_id: str, current_user: dict = Depends(get_current_user)):
    """Delete account group (soft delete)"""
    existing = await db.account_groups.find_one({"id": group_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Account group not found")
    
    if existing.get("is_system"):
        raise HTTPException(status_code=400, detail="Cannot delete system account group")
    
    # Check for child groups
    children = await db.account_groups.count_documents({"parent_id": group_id, "is_active": True})
    if children > 0:
        raise HTTPException(status_code=400, detail=f"Cannot delete. Has {children} child groups")
    
    # Check for ledgers
    ledgers = await db.ledgers.count_documents({"account_group_id": group_id, "is_active": True})
    if ledgers > 0:
        raise HTTPException(status_code=400, detail=f"Cannot delete. Has {ledgers} ledgers")
    
    await db.account_groups.update_one({"id": group_id}, {"$set": {"is_active": False}})
    return {"message": "Account group deleted"}


# ==================== LEDGERS ====================

@router.get("/ledgers")
async def get_ledgers(
    branch_id: Optional[str] = None,
    account_group_id: Optional[str] = None,
    is_party: Optional[bool] = None,
    search: Optional[str] = None,
    is_active: bool = True,
    current_user: dict = Depends(get_current_user)
):
    """Get all ledgers with filters"""
    query = {}
    if is_active is not None:
        query["is_active"] = is_active
    if branch_id:
        query["branch_id"] = branch_id
    if account_group_id:
        query["account_group_id"] = account_group_id
    if is_party is not None:
        query["is_party"] = is_party
    if search:
        query["name"] = {"$regex": search, "$options": "i"}
    
    ledgers = await db.ledgers.find(query, {"_id": 0}).to_list(10000)
    
    # Enrich with group info
    groups = await db.account_groups.find({}, {"_id": 0}).to_list(1000)
    groups_dict = {g["id"]: g for g in groups}
    
    for ledger in ledgers:
        group = groups_dict.get(ledger.get("account_group_id"), {})
        ledger["group_name"] = group.get("name", "Unknown")
        ledger["account_type"] = group.get("account_type", "Unknown")
    
    return ledgers


@router.get("/ledgers/{ledger_id}")
async def get_ledger(ledger_id: str, current_user: dict = Depends(get_current_user)):
    """Get ledger details"""
    ledger = await db.ledgers.find_one({"id": ledger_id}, {"_id": 0})
    if not ledger:
        raise HTTPException(status_code=404, detail="Ledger not found")
    
    group = await db.account_groups.find_one({"id": ledger["account_group_id"]}, {"_id": 0})
    ledger["group_name"] = group["name"] if group else "Unknown"
    ledger["account_type"] = group["account_type"] if group else "Unknown"
    
    return ledger


@router.post("/ledgers")
async def create_ledger(ledger_data: dict, current_user: dict = Depends(get_current_user)):
    """Create a new ledger"""
    # Validate account group
    group = await db.account_groups.find_one({"id": ledger_data["account_group_id"]})
    if not group:
        raise HTTPException(status_code=404, detail="Account group not found")
    
    # Set balance type from group nature
    if "balance_type" not in ledger_data:
        ledger_data["balance_type"] = group.get("nature", "debit")
    
    ledger_doc = {
        "id": str(uuid.uuid4()),
        **ledger_data,
        "current_balance": ledger_data.get("opening_balance", 0),
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.ledgers.insert_one(ledger_doc)
    
    # Post opening balance if not zero
    opening_balance = ledger_data.get("opening_balance", 0)
    if opening_balance != 0:
        voucher_number = await get_next_voucher_number(db, "journal", ledger_data.get("branch_id"))
        
        entry_type = ledger_data.get("balance_type", "debit")
        entries = [{
            "ledger_id": ledger_doc["id"],
            "ledger_name": ledger_doc["name"],
            "debit": abs(opening_balance) if entry_type == "debit" else 0,
            "credit": abs(opening_balance) if entry_type == "credit" else 0,
            "narration": "Opening Balance"
        }]
        
        voucher_doc = {
            "id": str(uuid.uuid4()),
            "voucher_type": "journal",
            "voucher_number": voucher_number,
            "voucher_date": datetime.now(timezone.utc).isoformat()[:10],
            "branch_id": ledger_data.get("branch_id"),
            "entries": entries,
            "narration": f"Opening Balance - {ledger_doc['name']}",
            "reference_type": "opening_balance",
            "reference_id": ledger_doc["id"],
            "total_debit": abs(opening_balance) if entry_type == "debit" else 0,
            "total_credit": abs(opening_balance) if entry_type == "credit" else 0,
            "status": "approved",
            "created_by": current_user["username"],
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.vouchers.insert_one(voucher_doc)
    
    ledger_doc.pop("_id", None)
    return ledger_doc


@router.put("/ledgers/{ledger_id}")
async def update_ledger(
    ledger_id: str,
    ledger_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Update ledger (cannot update opening balance after creation)"""
    existing = await db.ledgers.find_one({"id": ledger_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Ledger not found")
    
    # Remove protected fields
    ledger_data.pop("opening_balance", None)
    ledger_data.pop("current_balance", None)
    
    ledger_data["modified_at"] = datetime.now(timezone.utc).isoformat()
    await db.ledgers.update_one({"id": ledger_id}, {"$set": ledger_data})
    
    return {"message": "Ledger updated"}


@router.delete("/ledgers/{ledger_id}")
async def delete_ledger(ledger_id: str, current_user: dict = Depends(get_current_user)):
    """Soft delete ledger"""
    existing = await db.ledgers.find_one({"id": ledger_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Ledger not found")
    
    if existing.get("is_system"):
        raise HTTPException(status_code=400, detail="Cannot delete system ledger")
    
    # Check for voucher entries
    voucher_count = await db.vouchers.count_documents({"entries.ledger_id": ledger_id})
    if voucher_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete ledger with {voucher_count} voucher entries"
        )
    
    await db.ledgers.update_one({"id": ledger_id}, {"$set": {"is_active": False}})
    return {"message": "Ledger deleted"}


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
    ).sort([("voucher_date", 1), ("created_at", 1)]).to_list(10000)
    
    # Calculate opening balance if date filter
    opening_balance = ledger["opening_balance"]
    if start_date:
        prior_query = {"ledger_id": ledger_id, "voucher_date": {"$lt": start_date}}
        prior_trans = await db.ledger_transactions.find_one(
            prior_query,
            sort=[("voucher_date", -1), ("created_at", -1)]
        )
        if prior_trans:
            opening_balance = prior_trans["balance"]
    
    closing_balance = transactions[-1]["balance"] if transactions else opening_balance
    
    return {
        "ledger": ledger,
        "opening_balance": opening_balance,
        "transactions": transactions,
        "closing_balance": closing_balance,
        "total_transactions": len(transactions)
    }


# ==================== VOUCHERS ====================

@router.get("/vouchers")
async def get_vouchers(
    voucher_type: Optional[str] = None,
    branch_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 500,
    current_user: dict = Depends(get_current_user)
):
    """Get vouchers with filters"""
    query = {}
    if voucher_type:
        query["voucher_type"] = voucher_type
    if branch_id:
        query["branch_id"] = branch_id
    if status:
        query["status"] = status
    
    date_query = {}
    if start_date:
        date_query["$gte"] = start_date
    if end_date:
        date_query["$lte"] = end_date
    if date_query:
        query["voucher_date"] = date_query
    
    vouchers = await db.vouchers.find(
        query, {"_id": 0}
    ).sort("voucher_date", -1).to_list(limit)
    
    return vouchers


@router.get("/vouchers/{voucher_id}")
async def get_voucher(voucher_id: str, current_user: dict = Depends(get_current_user)):
    """Get voucher details"""
    voucher = await db.vouchers.find_one({"id": voucher_id}, {"_id": 0})
    if not voucher:
        raise HTTPException(status_code=404, detail="Voucher not found")
    return voucher


@router.post("/vouchers")
async def create_voucher(voucher_data: dict, current_user: dict = Depends(get_current_user)):
    """Create a new voucher with double-entry validation"""
    
    entries = voucher_data.get("entries", [])
    if not entries:
        raise HTTPException(status_code=400, detail="Voucher must have entries")
    
    # Calculate totals
    total_debit = sum(e.get("debit", 0) or 0 for e in entries)
    total_credit = sum(e.get("credit", 0) or 0 for e in entries)
    
    # Validate balance
    if abs(total_debit - total_credit) > 0.01:
        raise HTTPException(
            status_code=400,
            detail=f"Voucher not balanced. Dr: {total_debit}, Cr: {total_credit}"
        )
    
    # Validate ledgers exist
    for entry in entries:
        ledger = await db.ledgers.find_one({"id": entry["ledger_id"]})
        if not ledger:
            raise HTTPException(
                status_code=404,
                detail=f"Ledger not found: {entry.get('ledger_name', entry['ledger_id'])}"
            )
        entry["ledger_name"] = ledger["name"]
    
    # Generate voucher number
    voucher_number = await get_next_voucher_number(
        db, voucher_data["voucher_type"], voucher_data.get("branch_id")
    )
    
    voucher_doc = {
        "id": str(uuid.uuid4()),
        **voucher_data,
        "voucher_number": voucher_number,
        "total_debit": total_debit,
        "total_credit": total_credit,
        "status": "approved",
        "created_by": current_user["username"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.vouchers.insert_one(voucher_doc)
    
    # Post to ledgers
    await post_to_ledgers(
        db,
        voucher_doc["id"],
        voucher_number,
        voucher_data["voucher_type"],
        voucher_data["voucher_date"],
        voucher_data.get("branch_id"),
        entries
    )
    
    voucher_doc.pop("_id", None)
    return voucher_doc


@router.put("/vouchers/{voucher_id}")
async def update_voucher(
    voucher_id: str,
    voucher_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Update voucher (reverse and re-post)"""
    existing = await db.vouchers.find_one({"id": voucher_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Voucher not found")
    
    if existing.get("status") == "reversed":
        raise HTTPException(status_code=400, detail="Cannot modify reversed voucher")
    
    entries = voucher_data.get("entries", [])
    total_debit = sum(e.get("debit", 0) or 0 for e in entries)
    total_credit = sum(e.get("credit", 0) or 0 for e in entries)
    
    if abs(total_debit - total_credit) > 0.01:
        raise HTTPException(status_code=400, detail="Voucher not balanced")
    
    # Reverse old postings
    await reverse_ledger_postings(db, voucher_id)
    
    # Update voucher
    voucher_data["total_debit"] = total_debit
    voucher_data["total_credit"] = total_credit
    voucher_data["modified_at"] = datetime.now(timezone.utc).isoformat()
    voucher_data["modified_by"] = current_user["username"]
    
    await db.vouchers.update_one({"id": voucher_id}, {"$set": voucher_data})
    
    # Re-post to ledgers
    await post_to_ledgers(
        db,
        voucher_id,
        existing["voucher_number"],
        voucher_data.get("voucher_type", existing["voucher_type"]),
        voucher_data.get("voucher_date", existing["voucher_date"]),
        voucher_data.get("branch_id", existing.get("branch_id")),
        entries
    )
    
    return {"message": "Voucher updated"}


@router.delete("/vouchers/{voucher_id}")
async def delete_voucher(
    voucher_id: str,
    reason: str = "Deleted by user",
    current_user: dict = Depends(get_current_user)
):
    """Delete voucher by creating reversal entry (not hard delete)"""
    existing = await db.vouchers.find_one({"id": voucher_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Voucher not found")
    
    if existing.get("status") == "reversed":
        raise HTTPException(status_code=400, detail="Voucher already reversed")
    
    # Create reversal voucher
    result = await create_reversal_voucher(db, voucher_id, reason, current_user["username"])
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return {
        "message": "Voucher reversed successfully",
        "reversal_voucher": result["reversal_voucher"]["voucher_number"]
    }


# ==================== FINANCIAL REPORTS ====================

@router.get("/reports/day-book")
async def get_day_book(
    start_date: str,
    end_date: str,
    branch_id: Optional[str] = None,
    voucher_type: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get day book (all vouchers in date range)"""
    query = {
        "voucher_date": {"$gte": start_date, "$lte": end_date},
        "status": {"$ne": "reversed"}
    }
    if branch_id:
        query["branch_id"] = branch_id
    if voucher_type:
        query["voucher_type"] = voucher_type
    
    vouchers = await db.vouchers.find(query, {"_id": 0}).sort("voucher_date", 1).to_list(10000)
    
    total_debit = sum(v["total_debit"] for v in vouchers)
    total_credit = sum(v["total_credit"] for v in vouchers)
    
    return {
        "start_date": start_date,
        "end_date": end_date,
        "vouchers": vouchers,
        "total_vouchers": len(vouchers),
        "total_debit": total_debit,
        "total_credit": total_credit
    }


@router.get("/reports/trial-balance")
async def get_trial_balance_report(
    as_on_date: Optional[str] = None,
    branch_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get trial balance"""
    result = await calculate_trial_balance(db, branch_id, as_on_date)
    return result


@router.get("/reports/profit-loss")
async def get_profit_loss_report(
    start_date: str,
    end_date: str,
    branch_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get Profit & Loss statement"""
    result = await calculate_profit_loss(db, start_date, end_date, branch_id)
    return result


@router.get("/reports/balance-sheet")
async def get_balance_sheet_report(
    as_on_date: str,
    branch_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get Balance Sheet"""
    result = await calculate_balance_sheet(db, as_on_date, branch_id)
    return result
