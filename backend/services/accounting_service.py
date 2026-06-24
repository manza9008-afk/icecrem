"""
HOOREN ERP - Accounting Services
Complete Chart of Accounts and Ledger Posting Engine
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import uuid

DatabaseHandle = Any

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db_models import AccountGroup as DBAccountGroup
from db_models import Branch as DBBranch
from db_models import Ledger as DBLedger
from db_models import LedgerTransaction as DBLedgerTransaction
from db_models import Voucher as DBVoucher


def _is_sql_session(db: Any) -> bool:
    return isinstance(db, AsyncSession)

# Standard Indian Chart of Accounts Structure
STANDARD_CHART_OF_ACCOUNTS = [
    # Primary Groups
    {"code": "A", "name": "Assets", "type": "Asset", "nature": "debit", "parent": None, "affects_gp": False},
    {"code": "L", "name": "Liabilities", "type": "Liability", "nature": "credit", "parent": None, "affects_gp": False},
    {"code": "C", "name": "Capital Account", "type": "Capital", "nature": "credit", "parent": None, "affects_gp": False},
    {"code": "I", "name": "Income", "type": "Income", "nature": "credit", "parent": None, "affects_gp": False},
    {"code": "E", "name": "Expenses", "type": "Expense", "nature": "debit", "parent": None, "affects_gp": False},
    
    # Asset Sub-Groups
    {"code": "A01", "name": "Current Assets", "type": "Asset", "nature": "debit", "parent": "A", "affects_gp": False},
    {"code": "A0101", "name": "Cash-in-Hand", "type": "Asset", "nature": "debit", "parent": "A01", "affects_gp": False},
    {"code": "A0102", "name": "Bank Accounts", "type": "Asset", "nature": "debit", "parent": "A01", "affects_gp": False},
    {"code": "A0103", "name": "Sundry Debtors", "type": "Asset", "nature": "debit", "parent": "A01", "affects_gp": False},
    {"code": "A0104", "name": "Stock-in-Hand", "type": "Asset", "nature": "debit", "parent": "A01", "affects_gp": True},
    {"code": "A0105", "name": "Loans & Advances (Asset)", "type": "Asset", "nature": "debit", "parent": "A01", "affects_gp": False},
    {"code": "A0106", "name": "Deposits (Asset)", "type": "Asset", "nature": "debit", "parent": "A01", "affects_gp": False},
    
    {"code": "A02", "name": "Fixed Assets", "type": "Asset", "nature": "debit", "parent": "A", "affects_gp": False},
    {"code": "A0201", "name": "Land & Building", "type": "Asset", "nature": "debit", "parent": "A02", "affects_gp": False},
    {"code": "A0202", "name": "Plant & Machinery", "type": "Asset", "nature": "debit", "parent": "A02", "affects_gp": False},
    {"code": "A0203", "name": "Furniture & Fixtures", "type": "Asset", "nature": "debit", "parent": "A02", "affects_gp": False},
    {"code": "A0204", "name": "Vehicles", "type": "Asset", "nature": "debit", "parent": "A02", "affects_gp": False},
    {"code": "A0205", "name": "Computer & Electronics", "type": "Asset", "nature": "debit", "parent": "A02", "affects_gp": False},
    
    {"code": "A03", "name": "Investments", "type": "Asset", "nature": "debit", "parent": "A", "affects_gp": False},
    
    # Liability Sub-Groups
    {"code": "L01", "name": "Current Liabilities", "type": "Liability", "nature": "credit", "parent": "L", "affects_gp": False},
    {"code": "L0101", "name": "Sundry Creditors", "type": "Liability", "nature": "credit", "parent": "L01", "affects_gp": False},
    {"code": "L0102", "name": "Duties & Taxes", "type": "Liability", "nature": "credit", "parent": "L01", "affects_gp": False},
    {"code": "L0103", "name": "Provisions", "type": "Liability", "nature": "credit", "parent": "L01", "affects_gp": False},
    {"code": "L0104", "name": "Other Current Liabilities", "type": "Liability", "nature": "credit", "parent": "L01", "affects_gp": False},
    
    {"code": "L02", "name": "Loans (Liability)", "type": "Liability", "nature": "credit", "parent": "L", "affects_gp": False},
    {"code": "L0201", "name": "Secured Loans", "type": "Liability", "nature": "credit", "parent": "L02", "affects_gp": False},
    {"code": "L0202", "name": "Unsecured Loans", "type": "Liability", "nature": "credit", "parent": "L02", "affects_gp": False},
    {"code": "L0203", "name": "Bank OD/CC Account", "type": "Liability", "nature": "credit", "parent": "L02", "affects_gp": False},
    
    # Capital Sub-Groups
    {"code": "C01", "name": "Capital", "type": "Capital", "nature": "credit", "parent": "C", "affects_gp": False},
    {"code": "C02", "name": "Reserves & Surplus", "type": "Capital", "nature": "credit", "parent": "C", "affects_gp": False},
    {"code": "C03", "name": "Profit & Loss A/c", "type": "Capital", "nature": "credit", "parent": "C", "affects_gp": False},
    
    # Income Sub-Groups (Trading A/c)
    {"code": "I01", "name": "Sales Accounts", "type": "Income", "nature": "credit", "parent": "I", "affects_gp": True},
    {"code": "I0101", "name": "Sales - GST", "type": "Income", "nature": "credit", "parent": "I01", "affects_gp": True},
    {"code": "I0102", "name": "Sales - Non GST", "type": "Income", "nature": "credit", "parent": "I01", "affects_gp": True},
    {"code": "I0103", "name": "Sales Returns", "type": "Income", "nature": "debit", "parent": "I01", "affects_gp": True},
    
    # Income Sub-Groups (P&L A/c)
    {"code": "I02", "name": "Direct Income", "type": "Income", "nature": "credit", "parent": "I", "affects_gp": False},
    {"code": "I03", "name": "Indirect Income", "type": "Income", "nature": "credit", "parent": "I", "affects_gp": False},
    {"code": "I0301", "name": "Interest Received", "type": "Income", "nature": "credit", "parent": "I03", "affects_gp": False},
    {"code": "I0302", "name": "Discount Received", "type": "Income", "nature": "credit", "parent": "I03", "affects_gp": False},
    {"code": "I0303", "name": "Commission Received", "type": "Income", "nature": "credit", "parent": "I03", "affects_gp": False},
    {"code": "I0304", "name": "Rent Received", "type": "Income", "nature": "credit", "parent": "I03", "affects_gp": False},
    {"code": "I0305", "name": "Miscellaneous Income", "type": "Income", "nature": "credit", "parent": "I03", "affects_gp": False},
    
    # Expense Sub-Groups (Trading A/c)
    {"code": "E01", "name": "Purchase Accounts", "type": "Expense", "nature": "debit", "parent": "E", "affects_gp": True},
    {"code": "E0101", "name": "Purchases - GST", "type": "Expense", "nature": "debit", "parent": "E01", "affects_gp": True},
    {"code": "E0102", "name": "Purchases - Non GST", "type": "Expense", "nature": "debit", "parent": "E01", "affects_gp": True},
    {"code": "E0103", "name": "Purchase Returns", "type": "Expense", "nature": "credit", "parent": "E01", "affects_gp": True},
    
    {"code": "E02", "name": "Direct Expenses", "type": "Expense", "nature": "debit", "parent": "E", "affects_gp": True},
    {"code": "E0201", "name": "Carriage Inward", "type": "Expense", "nature": "debit", "parent": "E02", "affects_gp": True},
    {"code": "E0202", "name": "Wages", "type": "Expense", "nature": "debit", "parent": "E02", "affects_gp": True},
    {"code": "E0203", "name": "Manufacturing Expenses", "type": "Expense", "nature": "debit", "parent": "E02", "affects_gp": True},
    
    # Expense Sub-Groups (P&L A/c)
    {"code": "E03", "name": "Indirect Expenses", "type": "Expense", "nature": "debit", "parent": "E", "affects_gp": False},
    {"code": "E0301", "name": "Salaries & Wages", "type": "Expense", "nature": "debit", "parent": "E03", "affects_gp": False},
    {"code": "E0302", "name": "Rent & Rates", "type": "Expense", "nature": "debit", "parent": "E03", "affects_gp": False},
    {"code": "E0303", "name": "Electricity & Water", "type": "Expense", "nature": "debit", "parent": "E03", "affects_gp": False},
    {"code": "E0304", "name": "Telephone & Internet", "type": "Expense", "nature": "debit", "parent": "E03", "affects_gp": False},
    {"code": "E0305", "name": "Printing & Stationery", "type": "Expense", "nature": "debit", "parent": "E03", "affects_gp": False},
    {"code": "E0306", "name": "Travelling & Conveyance", "type": "Expense", "nature": "debit", "parent": "E03", "affects_gp": False},
    {"code": "E0307", "name": "Legal & Professional Fees", "type": "Expense", "nature": "debit", "parent": "E03", "affects_gp": False},
    {"code": "E0308", "name": "Bank Charges", "type": "Expense", "nature": "debit", "parent": "E03", "affects_gp": False},
    {"code": "E0309", "name": "Interest Paid", "type": "Expense", "nature": "debit", "parent": "E03", "affects_gp": False},
    {"code": "E0310", "name": "Discount Allowed", "type": "Expense", "nature": "debit", "parent": "E03", "affects_gp": False},
    {"code": "E0311", "name": "Depreciation", "type": "Expense", "nature": "debit", "parent": "E03", "affects_gp": False},
    {"code": "E0312", "name": "Bad Debts", "type": "Expense", "nature": "debit", "parent": "E03", "affects_gp": False},
    {"code": "E0313", "name": "Repairs & Maintenance", "type": "Expense", "nature": "debit", "parent": "E03", "affects_gp": False},
    {"code": "E0314", "name": "Insurance", "type": "Expense", "nature": "debit", "parent": "E03", "affects_gp": False},
    {"code": "E0315", "name": "Advertisement", "type": "Expense", "nature": "debit", "parent": "E03", "affects_gp": False},
    {"code": "E0316", "name": "Carriage Outward", "type": "Expense", "nature": "debit", "parent": "E03", "affects_gp": False},
    {"code": "E0317", "name": "Miscellaneous Expenses", "type": "Expense", "nature": "debit", "parent": "E03", "affects_gp": False},
    {"code": "E0318", "name": "Round Off", "type": "Expense", "nature": "debit", "parent": "E03", "affects_gp": False},
]

# GST Ledgers to be created
GST_LEDGERS = [
    {"name": "CGST Input", "group_code": "L0102", "nature": "debit"},
    {"name": "CGST Output", "group_code": "L0102", "nature": "credit"},
    {"name": "SGST Input", "group_code": "L0102", "nature": "debit"},
    {"name": "SGST Output", "group_code": "L0102", "nature": "credit"},
    {"name": "IGST Input", "group_code": "L0102", "nature": "debit"},
    {"name": "IGST Output", "group_code": "L0102", "nature": "credit"},
    {"name": "CESS Input", "group_code": "L0102", "nature": "debit"},
    {"name": "CESS Output", "group_code": "L0102", "nature": "credit"},
    {"name": "TDS Payable", "group_code": "L0102", "nature": "credit"},
    {"name": "TCS Payable", "group_code": "L0102", "nature": "credit"},
]


async def seed_chart_of_accounts(db: DatabaseHandle, branch_id: str):
    """Seed standard Indian Chart of Accounts"""
    if _is_sql_session(db):
        existing = await db.execute(select(func.count(DBAccountGroup.id)))
        existing_count = existing.scalar() or 0
        if existing_count > 0:
            return {"message": "Chart of accounts already exists", "count": existing_count}

        code_to_id = {}
        for group_data in STANDARD_CHART_OF_ACCOUNTS:
            group_id = str(uuid.uuid4())
            code_to_id[group_data["code"]] = group_id
            parent_id = code_to_id.get(group_data["parent"]) if group_data["parent"] else None
            db.add(DBAccountGroup(
                id=group_id,
                code=group_data["code"],
                name=group_data["name"],
                account_type=group_data["type"],
                nature=group_data["nature"],
                parent_id=parent_id,
                affects_gross_profit=group_data["affects_gp"],
                is_system=True,
                is_active=True,
                created_at=datetime.now(timezone.utc),
            ))

        await db.flush()

        standard_ledgers = [
            *GST_LEDGERS,
            {"name": "Cash", "group_code": "A0101", "nature": "debit"},
            {"name": "Sales Account", "group_code": "I0101", "nature": "credit"},
            {"name": "Sales - Kacha Bill", "group_code": "I0102", "nature": "credit"},
            {"name": "Purchase Account", "group_code": "E0101", "nature": "debit"},
            {"name": "Opening Stock", "group_code": "A0104", "nature": "debit"},
            {"name": "Closing Stock", "group_code": "A0104", "nature": "debit"},
            {"name": "Profit & Loss Account", "group_code": "C03", "nature": "credit"},
        ]

        for ledger_data in standard_ledgers:
            group_id = code_to_id.get(ledger_data["group_code"])
            if not group_id:
                continue
            db.add(DBLedger(
                id=str(uuid.uuid4()),
                name=ledger_data["name"],
                code=ledger_data["name"].upper().replace(" ", "_"),
                account_group_id=group_id,
                branch_id=branch_id,
                opening_balance=0.0,
                balance_type=ledger_data.get("nature", "debit"),
                current_balance=0.0,
                is_party=False,
                is_system=True,
                is_active=True,
                created_at=datetime.now(timezone.utc),
            ))

        await db.commit()
        return {"message": "Chart of accounts seeded successfully", "groups": len(STANDARD_CHART_OF_ACCOUNTS)}
    
    # Check if already seeded
    existing_count = await db.account_groups.count_documents({})
    if existing_count > 0:
        return {"message": "Chart of accounts already exists", "count": existing_count}
    
    code_to_id = {}
    
    # First pass - create all groups
    for group_data in STANDARD_CHART_OF_ACCOUNTS:
        group_id = str(uuid.uuid4())
        code_to_id[group_data["code"]] = group_id
        
        parent_id = None
        if group_data["parent"]:
            parent_id = code_to_id.get(group_data["parent"])
        
        group_doc = {
            "id": group_id,
            "code": group_data["code"],
            "name": group_data["name"],
            "account_type": group_data["type"],
            "nature": group_data["nature"],
            "parent_id": parent_id,
            "affects_gross_profit": group_data["affects_gp"],
            "is_system": True,
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.account_groups.insert_one(group_doc)
    
    # Create GST ledgers
    for ledger_data in GST_LEDGERS:
        group_id = code_to_id.get(ledger_data["group_code"])
        if group_id:
            ledger_doc = {
                "id": str(uuid.uuid4()),
                "name": ledger_data["name"],
                "code": ledger_data["name"].upper().replace(" ", "_"),
                "account_group_id": group_id,
                "branch_id": branch_id,
                "opening_balance": 0.0,
                "balance_type": ledger_data["nature"],
                "current_balance": 0.0,
                "is_party": False,
                "is_system": True,
                "is_active": True,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.ledgers.insert_one(ledger_doc)
    
    # Create standard ledgers
    standard_ledgers = [
        {"name": "Cash", "group_code": "A0101"},
        {"name": "Sales Account", "group_code": "I0101"},
        {"name": "Sales - Kacha Bill", "group_code": "I0102"},
        {"name": "Purchase Account", "group_code": "E0101"},
        {"name": "Opening Stock", "group_code": "A0104"},
        {"name": "Closing Stock", "group_code": "A0104"},
        {"name": "Profit & Loss Account", "group_code": "C03"},
    ]
    
    for ledger_data in standard_ledgers:
        group_id = code_to_id.get(ledger_data["group_code"])
        if group_id:
            group = await db.account_groups.find_one({"id": group_id})
            ledger_doc = {
                "id": str(uuid.uuid4()),
                "name": ledger_data["name"],
                "code": ledger_data["name"].upper().replace(" ", "_"),
                "account_group_id": group_id,
                "branch_id": branch_id,
                "opening_balance": 0.0,
                "balance_type": group["nature"] if group else "debit",
                "current_balance": 0.0,
                "is_party": False,
                "is_system": True,
                "is_active": True,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.ledgers.insert_one(ledger_doc)
    
    return {"message": "Chart of accounts seeded successfully", "groups": len(STANDARD_CHART_OF_ACCOUNTS)}


async def post_to_ledgers(
    db: DatabaseHandle,
    voucher_id: str,
    voucher_number: str,
    voucher_type: str,
    voucher_date: str,
    branch_id: str,
    entries: List[Dict[str, Any]],
    is_reversal: bool = False
):
    """Post voucher entries to ledgers with running balance"""
    if _is_sql_session(db):
        for entry in entries:
            ledger_id = entry["ledger_id"]
            debit = entry.get("debit", 0) or 0
            credit = entry.get("credit", 0) or 0
            if is_reversal:
                debit, credit = credit, debit

            result = await db.execute(select(DBLedger).where(DBLedger.id == ledger_id))
            ledger = result.scalar_one_or_none()
            if not ledger:
                continue

            balance_change = debit - credit if ledger.balance_type == "debit" else credit - debit
            ledger.current_balance = (ledger.current_balance or 0) + balance_change

            db.add(DBLedgerTransaction(
                id=str(uuid.uuid4()),
                ledger_id=ledger_id,
                voucher_id=voucher_id,
                voucher_number=voucher_number,
                voucher_type=voucher_type,
                voucher_date=voucher_date,
                branch_id=branch_id,
                debit=debit,
                credit=credit,
                balance=ledger.current_balance,
                narration=entry.get("narration"),
                created_at=datetime.now(timezone.utc),
            ))
        return True
    
    for entry in entries:
        ledger_id = entry["ledger_id"]
        debit = entry.get("debit", 0) or 0
        credit = entry.get("credit", 0) or 0
        
        # For reversal, swap debit/credit
        if is_reversal:
            debit, credit = credit, debit
        
        # Get current ledger
        ledger = await db.ledgers.find_one({"id": ledger_id})
        if not ledger:
            continue
        
        # Calculate balance change based on nature
        # Debit increases debit nature accounts, Credit increases credit nature accounts
        if ledger["balance_type"] == "debit":
            balance_change = debit - credit
        else:
            balance_change = credit - debit
        
        # Update ledger balance
        new_balance = ledger["current_balance"] + balance_change
        await db.ledgers.update_one(
            {"id": ledger_id},
            {"$set": {"current_balance": new_balance}}
        )
        
        # Create ledger transaction entry
        transaction_doc = {
            "id": str(uuid.uuid4()),
            "ledger_id": ledger_id,
            "voucher_id": voucher_id,
            "voucher_number": voucher_number,
            "voucher_type": voucher_type,
            "voucher_date": voucher_date,
            "branch_id": branch_id,
            "debit": debit,
            "credit": credit,
            "balance": new_balance,
            "narration": entry.get("narration"),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.ledger_transactions.insert_one(transaction_doc)
    
    return True


async def reverse_ledger_postings(db: DatabaseHandle, voucher_id: str):
    """Reverse all ledger postings for a voucher"""
    
    transactions = await db.ledger_transactions.find({"voucher_id": voucher_id}).to_list(1000)
    
    for trans in transactions:
        ledger = await db.ledgers.find_one({"id": trans["ledger_id"]})
        if not ledger:
            continue
        
        # Reverse the balance change
        if ledger["balance_type"] == "debit":
            balance_change = trans["credit"] - trans["debit"]
        else:
            balance_change = trans["debit"] - trans["credit"]
        
        new_balance = ledger["current_balance"] + balance_change
        await db.ledgers.update_one(
            {"id": trans["ledger_id"]},
            {"$set": {"current_balance": new_balance}}
        )
    
    # Delete the transaction entries
    await db.ledger_transactions.delete_many({"voucher_id": voucher_id})
    
    return True


async def get_next_voucher_number(
    db: DatabaseHandle,
    voucher_type: str,
    branch_id: Optional[str] = None,
    financial_year: str = "2025-26"
) -> str:
    """Generate next voucher number with branch code"""
    
    prefix_map = {
        "journal": "JV",
        "payment": "PV",
        "receipt": "RV",
        "contra": "CV",
        "debit_note": "DN",
        "credit_note": "CN",
        "sales": "SI",
        "purchase": "PI"
    }
    
    prefix = prefix_map.get(voucher_type, "VC")
    branch_code = ""

    if _is_sql_session(db):
        if branch_id:
            result = await db.execute(select(DBBranch).where(DBBranch.id == branch_id))
            branch = result.scalar_one_or_none()
            if branch:
                branch_code = f"{branch.code}/"

        query = select(DBVoucher).where(DBVoucher.voucher_type == voucher_type)
        if branch_id:
            query = query.where(DBVoucher.branch_id == branch_id)
        query = query.order_by(desc(DBVoucher.created_at)).limit(1)

        result = await db.execute(query)
        last_voucher = result.scalar_one_or_none()
        if last_voucher and last_voucher.voucher_number:
            try:
                new_num = int(last_voucher.voucher_number.split("/")[-1]) + 1
            except (ValueError, IndexError):
                new_num = 1
        else:
            new_num = 1

        return f"{prefix}/{branch_code}{financial_year}/{new_num:05d}"
    
    if branch_id:
        branch = await db.branches.find_one({"id": branch_id})
        if branch:
            branch_code = f"{branch['code']}/"
    
    # Get last voucher number for this type and branch
    query = {"voucher_type": voucher_type}
    if branch_id:
        query["branch_id"] = branch_id
    
    last_voucher = await db.vouchers.find_one(
        query,
        sort=[("created_at", -1)]
    )
    
    if last_voucher and "voucher_number" in last_voucher:
        try:
            parts = last_voucher["voucher_number"].split("/")
            last_num = int(parts[-1])
            new_num = last_num + 1
        except:
            new_num = 1
    else:
        new_num = 1
    
    return f"{prefix}/{branch_code}{financial_year}/{new_num:05d}"


async def create_reversal_voucher(
    db: DatabaseHandle,
    original_voucher_id: str,
    reason: str,
    created_by: str
) -> Dict[str, Any]:
    """Create a reversal voucher for the original voucher"""
    
    original = await db.vouchers.find_one({"id": original_voucher_id})
    if not original:
        return {"error": "Original voucher not found"}
    
    # Generate reversal voucher number
    voucher_number = await get_next_voucher_number(
        db, original["voucher_type"], original.get("branch_id")
    )
    
    # Swap debit/credit in entries
    reversed_entries = []
    for entry in original["entries"]:
        reversed_entries.append({
            "id": str(uuid.uuid4()),
            "ledger_id": entry["ledger_id"],
            "ledger_name": entry["ledger_name"],
            "debit": entry.get("credit", 0),
            "credit": entry.get("debit", 0),
            "narration": f"Reversal: {entry.get('narration', '')}"
        })
    
    # Create reversal voucher
    reversal_doc = {
        "id": str(uuid.uuid4()),
        "voucher_type": original["voucher_type"],
        "voucher_number": voucher_number,
        "voucher_date": datetime.now(timezone.utc).isoformat()[:10],
        "branch_id": original.get("branch_id"),
        "entries": reversed_entries,
        "narration": f"Reversal of {original['voucher_number']} - {reason}",
        "reference_type": "reversal",
        "reference_id": original_voucher_id,
        "is_reversal": True,
        "reversed_voucher_id": original_voucher_id,
        "total_debit": original["total_credit"],
        "total_credit": original["total_debit"],
        "status": "approved",
        "created_by": created_by,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.vouchers.insert_one(reversal_doc)
    
    # Post reversal entries
    await post_to_ledgers(
        db,
        reversal_doc["id"],
        reversal_doc["voucher_number"],
        reversal_doc["voucher_type"],
        reversal_doc["voucher_date"],
        reversal_doc.get("branch_id"),
        reversed_entries
    )
    
    # Mark original voucher as reversed
    await db.vouchers.update_one(
        {"id": original_voucher_id},
        {"$set": {"status": "reversed", "reversed_by": reversal_doc["id"]}}
    )
    
    return {"reversal_voucher": reversal_doc}


async def calculate_trial_balance(
    db: DatabaseHandle,
    branch_id: Optional[str] = None,
    as_on_date: Optional[str] = None
) -> Dict[str, Any]:
    """Calculate trial balance with proper grouping"""
    
    query = {"is_active": True}
    if branch_id:
        query["branch_id"] = branch_id
    
    ledgers = await db.ledgers.find(query, {"_id": 0}).to_list(10000)
    groups = await db.account_groups.find({}, {"_id": 0}).to_list(1000)
    groups_dict = {g["id"]: g for g in groups}
    
    items = []
    total_debit = 0.0
    total_credit = 0.0
    
    for ledger in ledgers:
        balance = ledger["current_balance"]
        group = groups_dict.get(ledger["account_group_id"], {})
        
        # Determine if balance is Dr or Cr
        if balance >= 0:
            debit = balance
            credit = 0.0
        else:
            debit = 0.0
            credit = abs(balance)
        
        total_debit += debit
        total_credit += credit
        
        items.append({
            "ledger_id": ledger["id"],
            "ledger_name": ledger["name"],
            "group_name": group.get("name", "Unknown"),
            "account_type": group.get("account_type", "Unknown"),
            "opening_debit": 0.0,
            "opening_credit": 0.0,
            "debit": debit,
            "credit": credit,
            "closing_debit": debit,
            "closing_credit": credit
        })
    
    # Sort by account type and name
    type_order = {"Asset": 0, "Liability": 1, "Capital": 2, "Income": 3, "Expense": 4}
    items.sort(key=lambda x: (type_order.get(x["account_type"], 5), x["ledger_name"]))
    
    difference = abs(total_debit - total_credit)
    
    return {
        "as_on_date": as_on_date or datetime.now(timezone.utc).isoformat()[:10],
        "branch_id": branch_id,
        "items": items,
        "total_debit": round(total_debit, 2),
        "total_credit": round(total_credit, 2),
        "difference": round(difference, 2),
        "is_balanced": difference < 0.01
    }


async def calculate_profit_loss(
    db: DatabaseHandle,
    start_date: str,
    end_date: str,
    branch_id: Optional[str] = None
) -> Dict[str, Any]:
    """Calculate Profit & Loss Statement"""
    
    # Get account groups
    income_groups = await db.account_groups.find({"account_type": "Income"}, {"_id": 0}).to_list(100)
    expense_groups = await db.account_groups.find({"account_type": "Expense"}, {"_id": 0}).to_list(100)
    
    income_group_ids = [g["id"] for g in income_groups]
    expense_group_ids = [g["id"] for g in expense_groups]
    
    groups_dict = {g["id"]: g for g in (income_groups + expense_groups)}
    
    # Build ledger query
    query = {"is_active": True}
    if branch_id:
        query["branch_id"] = branch_id
    
    all_ledgers = await db.ledgers.find(query, {"_id": 0}).to_list(10000)
    
    # Separate income and expense ledgers
    income_ledgers = [l for l in all_ledgers if l["account_group_id"] in income_group_ids]
    expense_ledgers = [l for l in all_ledgers if l["account_group_id"] in expense_group_ids]
    
    # Group by account group
    income_by_group = {}
    expense_by_group = {}
    
    for ledger in income_ledgers:
        group = groups_dict.get(ledger["account_group_id"], {})
        group_name = group.get("name", "Other Income")
        if group_name not in income_by_group:
            income_by_group[group_name] = {"ledgers": [], "total": 0}
        income_by_group[group_name]["ledgers"].append({
            "name": ledger["name"],
            "amount": abs(ledger["current_balance"])
        })
        income_by_group[group_name]["total"] += abs(ledger["current_balance"])
    
    for ledger in expense_ledgers:
        group = groups_dict.get(ledger["account_group_id"], {})
        group_name = group.get("name", "Other Expenses")
        if group_name not in expense_by_group:
            expense_by_group[group_name] = {"ledgers": [], "total": 0}
        expense_by_group[group_name]["ledgers"].append({
            "name": ledger["name"],
            "amount": abs(ledger["current_balance"])
        })
        expense_by_group[group_name]["total"] += abs(ledger["current_balance"])
    
    total_income = sum(g["total"] for g in income_by_group.values())
    total_expense = sum(g["total"] for g in expense_by_group.values())
    net_profit = total_income - total_expense
    
    return {
        "period_start": start_date,
        "period_end": end_date,
        "branch_id": branch_id,
        "income_items": [
            {"group_name": k, "ledgers": v["ledgers"], "total": round(v["total"], 2)}
            for k, v in income_by_group.items()
        ],
        "expense_items": [
            {"group_name": k, "ledgers": v["ledgers"], "total": round(v["total"], 2)}
            for k, v in expense_by_group.items()
        ],
        "total_income": round(total_income, 2),
        "total_expense": round(total_expense, 2),
        "gross_profit": round(total_income - total_expense, 2),
        "net_profit": round(net_profit, 2)
    }


async def calculate_balance_sheet(
    db: DatabaseHandle,
    as_on_date: str,
    branch_id: Optional[str] = None
) -> Dict[str, Any]:
    """Calculate Balance Sheet"""
    
    # Get P&L for net profit
    pl = await calculate_profit_loss(db, "2025-04-01", as_on_date, branch_id)
    net_profit = pl["net_profit"]
    
    # Get account groups
    asset_groups = await db.account_groups.find({"account_type": "Asset"}, {"_id": 0}).to_list(100)
    liability_groups = await db.account_groups.find({"account_type": "Liability"}, {"_id": 0}).to_list(100)
    capital_groups = await db.account_groups.find({"account_type": "Capital"}, {"_id": 0}).to_list(100)
    
    asset_group_ids = [g["id"] for g in asset_groups]
    liability_group_ids = [g["id"] for g in liability_groups]
    capital_group_ids = [g["id"] for g in capital_groups]
    
    groups_dict = {g["id"]: g for g in (asset_groups + liability_groups + capital_groups)}
    
    # Build query
    query = {"is_active": True}
    if branch_id:
        query["branch_id"] = branch_id
    
    all_ledgers = await db.ledgers.find(query, {"_id": 0}).to_list(10000)
    
    # Separate ledgers
    asset_ledgers = [l for l in all_ledgers if l["account_group_id"] in asset_group_ids]
    liability_ledgers = [l for l in all_ledgers if l["account_group_id"] in liability_group_ids]
    capital_ledgers = [l for l in all_ledgers if l["account_group_id"] in capital_group_ids]
    
    # Group by account group
    def group_ledgers(ledgers, groups):
        by_group = {}
        for ledger in ledgers:
            group = groups_dict.get(ledger["account_group_id"], {})
            group_name = group.get("name", "Other")
            if group_name not in by_group:
                by_group[group_name] = {"ledgers": [], "total": 0}
            by_group[group_name]["ledgers"].append({
                "name": ledger["name"],
                "amount": abs(ledger["current_balance"])
            })
            by_group[group_name]["total"] += abs(ledger["current_balance"])
        return by_group
    
    asset_by_group = group_ledgers(asset_ledgers, asset_groups)
    liability_by_group = group_ledgers(liability_ledgers, liability_groups)
    capital_by_group = group_ledgers(capital_ledgers, capital_groups)
    
    total_assets = sum(g["total"] for g in asset_by_group.values())
    total_liabilities = sum(g["total"] for g in liability_by_group.values())
    total_capital = sum(g["total"] for g in capital_by_group.values())
    
    # Add net profit to capital
    total_capital_with_profit = total_capital + net_profit
    
    return {
        "as_on_date": as_on_date,
        "branch_id": branch_id,
        "asset_items": [
            {"group_name": k, "ledgers": v["ledgers"], "total": round(v["total"], 2)}
            for k, v in asset_by_group.items()
        ],
        "liability_items": [
            {"group_name": k, "ledgers": v["ledgers"], "total": round(v["total"], 2)}
            for k, v in liability_by_group.items()
        ],
        "capital_items": [
            {"group_name": k, "ledgers": v["ledgers"], "total": round(v["total"], 2)}
            for k, v in capital_by_group.items()
        ],
        "total_assets": round(total_assets, 2),
        "total_liabilities": round(total_liabilities, 2),
        "total_capital": round(total_capital, 2),
        "net_profit": round(net_profit, 2),
        "total_liabilities_and_capital": round(total_liabilities + total_capital_with_profit, 2),
        "is_balanced": abs(total_assets - (total_liabilities + total_capital_with_profit)) < 0.01
    }
