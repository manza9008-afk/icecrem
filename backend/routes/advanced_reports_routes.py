"""
HOOREN ERP - Advanced Reports Routes
Ledger Account View, Group Summary, Outstanding Analysis, Aging Reports, Ratio Analysis
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import uuid

router = APIRouter(prefix="/api/reports", tags=["reports"])

from server import db
from utils import get_current_user


# ==================== LEDGER ACCOUNT VIEW ====================

@router.get("/ledger-account/{ledger_id}")
async def get_ledger_account_view(
    ledger_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get detailed ledger account statement with running balance"""
    ledger = await db.ledgers.find_one({"id": ledger_id}, {"_id": 0})
    if not ledger:
        raise HTTPException(status_code=404, detail="Ledger not found")
    
    # Get account group
    group = await db.account_groups.find_one({"id": ledger["account_group_id"]}, {"_id": 0})
    
    # Build transaction query
    query = {"ledger_id": ledger_id}
    if start_date or end_date:
        date_query = {}
        if start_date:
            date_query["$gte"] = start_date
        if end_date:
            date_query["$lte"] = end_date
        if date_query:
            query["voucher_date"] = date_query
    
    transactions = await db.ledger_transactions.find(
        query, {"_id": 0}
    ).sort([("voucher_date", 1), ("created_at", 1)]).to_list(10000)
    
    # Calculate opening balance
    opening_balance = ledger.get("opening_balance", 0)
    if start_date:
        prior_transactions = await db.ledger_transactions.find(
            {"ledger_id": ledger_id, "voucher_date": {"$lt": start_date}},
            {"_id": 0}
        ).to_list(10000)
        
        for trans in prior_transactions:
            if ledger.get("balance_type") == "debit":
                opening_balance += trans.get("debit", 0) - trans.get("credit", 0)
            else:
                opening_balance += trans.get("credit", 0) - trans.get("debit", 0)
    
    # Calculate running balance
    running_balance = opening_balance
    for trans in transactions:
        if ledger.get("balance_type") == "debit":
            running_balance += trans.get("debit", 0) - trans.get("credit", 0)
        else:
            running_balance += trans.get("credit", 0) - trans.get("debit", 0)
        trans["running_balance"] = round(running_balance, 2)
    
    total_debit = sum(t.get("debit", 0) for t in transactions)
    total_credit = sum(t.get("credit", 0) for t in transactions)
    
    return {
        "ledger": {
            **ledger,
            "group_name": group.get("name") if group else "Unknown",
            "account_type": group.get("account_type") if group else "Unknown"
        },
        "period": {
            "start_date": start_date,
            "end_date": end_date
        },
        "opening_balance": round(opening_balance, 2),
        "transactions": transactions,
        "total_debit": round(total_debit, 2),
        "total_credit": round(total_credit, 2),
        "closing_balance": round(running_balance, 2),
        "total_transactions": len(transactions)
    }


# ==================== GROUP SUMMARY ====================

@router.get("/group-summary")
async def get_group_summary(
    account_type: Optional[str] = None,
    branch_id: Optional[str] = None,
    as_on_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get summary of ledger balances grouped by account group"""
    
    # Get account groups
    group_query = {}
    if account_type:
        group_query["account_type"] = account_type
    
    groups = await db.account_groups.find(group_query, {"_id": 0}).to_list(1000)
    groups_dict = {g["id"]: g for g in groups}
    
    # Get ledgers
    ledger_query = {"is_active": True}
    if branch_id:
        ledger_query["branch_id"] = branch_id
    
    ledgers = await db.ledgers.find(ledger_query, {"_id": 0}).to_list(10000)
    
    # Group ledgers by account group
    group_summaries = {}
    
    for ledger in ledgers:
        group_id = ledger.get("account_group_id")
        if group_id not in groups_dict:
            continue
        
        group = groups_dict[group_id]
        
        if group_id not in group_summaries:
            group_summaries[group_id] = {
                "group_id": group_id,
                "group_code": group.get("code"),
                "group_name": group.get("name"),
                "account_type": group.get("account_type"),
                "nature": group.get("nature"),
                "ledgers": [],
                "total_debit": 0,
                "total_credit": 0
            }
        
        balance = ledger.get("current_balance", 0)
        
        if balance >= 0:
            debit = balance
            credit = 0
        else:
            debit = 0
            credit = abs(balance)
        
        group_summaries[group_id]["ledgers"].append({
            "ledger_id": ledger["id"],
            "ledger_name": ledger["name"],
            "debit": debit,
            "credit": credit
        })
        
        group_summaries[group_id]["total_debit"] += debit
        group_summaries[group_id]["total_credit"] += credit
    
    # Convert to list and sort
    summaries = list(group_summaries.values())
    type_order = {"Asset": 0, "Liability": 1, "Capital": 2, "Income": 3, "Expense": 4}
    summaries.sort(key=lambda x: (type_order.get(x["account_type"], 5), x["group_name"]))
    
    # Calculate grand totals
    grand_debit = sum(s["total_debit"] for s in summaries)
    grand_credit = sum(s["total_credit"] for s in summaries)
    
    return {
        "as_on_date": as_on_date or datetime.now(timezone.utc).isoformat()[:10],
        "branch_id": branch_id,
        "account_type": account_type,
        "groups": summaries,
        "grand_total_debit": round(grand_debit, 2),
        "grand_total_credit": round(grand_credit, 2),
        "total_groups": len(summaries)
    }


# ==================== OUTSTANDING ANALYSIS ====================

@router.get("/outstanding/receivables")
async def get_receivables_outstanding(
    branch_id: Optional[str] = None,
    as_on_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get outstanding receivables (Sundry Debtors)"""
    
    # Find Sundry Debtors group
    debtors_group = await db.account_groups.find_one({"code": "A0103"})
    if not debtors_group:
        return {"error": "Sundry Debtors group not found", "parties": [], "total": 0}
    
    # Get debtors ledgers
    query = {"account_group_id": debtors_group["id"], "is_active": True}
    if branch_id:
        query["branch_id"] = branch_id
    
    debtors = await db.ledgers.find(query, {"_id": 0}).to_list(10000)
    
    parties = []
    total_outstanding = 0
    
    for debtor in debtors:
        balance = debtor.get("current_balance", 0)
        if balance > 0:  # Only include positive balances (amounts owed to us)
            parties.append({
                "party_id": debtor["id"],
                "party_name": debtor["name"],
                "gstin": debtor.get("gstin"),
                "phone": debtor.get("phone"),
                "credit_days": debtor.get("credit_days", 0),
                "credit_limit": debtor.get("credit_limit", 0),
                "outstanding": round(balance, 2)
            })
            total_outstanding += balance
    
    # Sort by outstanding amount descending
    parties.sort(key=lambda x: x["outstanding"], reverse=True)
    
    return {
        "as_on_date": as_on_date or datetime.now(timezone.utc).isoformat()[:10],
        "branch_id": branch_id,
        "parties": parties,
        "total_outstanding": round(total_outstanding, 2),
        "total_parties": len(parties)
    }


@router.get("/outstanding/payables")
async def get_payables_outstanding(
    branch_id: Optional[str] = None,
    as_on_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get outstanding payables (Sundry Creditors)"""
    
    # Find Sundry Creditors group
    creditors_group = await db.account_groups.find_one({"code": "L0101"})
    if not creditors_group:
        return {"error": "Sundry Creditors group not found", "parties": [], "total": 0}
    
    # Get creditors ledgers
    query = {"account_group_id": creditors_group["id"], "is_active": True}
    if branch_id:
        query["branch_id"] = branch_id
    
    creditors = await db.ledgers.find(query, {"_id": 0}).to_list(10000)
    
    parties = []
    total_outstanding = 0
    
    for creditor in creditors:
        balance = creditor.get("current_balance", 0)
        if balance > 0:  # Credit balance means we owe them
            parties.append({
                "party_id": creditor["id"],
                "party_name": creditor["name"],
                "gstin": creditor.get("gstin"),
                "phone": creditor.get("phone"),
                "credit_days": creditor.get("credit_days", 0),
                "outstanding": round(balance, 2)
            })
            total_outstanding += balance
    
    parties.sort(key=lambda x: x["outstanding"], reverse=True)
    
    return {
        "as_on_date": as_on_date or datetime.now(timezone.utc).isoformat()[:10],
        "branch_id": branch_id,
        "parties": parties,
        "total_outstanding": round(total_outstanding, 2),
        "total_parties": len(parties)
    }


# ==================== AGING ANALYSIS ====================

@router.get("/aging/receivables")
async def get_receivables_aging(
    branch_id: Optional[str] = None,
    as_on_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get aging analysis of receivables"""
    
    if not as_on_date:
        as_on_date = datetime.now(timezone.utc).isoformat()[:10]
    
    reference_date = datetime.fromisoformat(as_on_date)
    
    # Age buckets
    buckets = {
        "0-30": {"min": 0, "max": 30, "amount": 0, "count": 0},
        "31-60": {"min": 31, "max": 60, "amount": 0, "count": 0},
        "61-90": {"min": 61, "max": 90, "amount": 0, "count": 0},
        "91-120": {"min": 91, "max": 120, "amount": 0, "count": 0},
        "120+": {"min": 121, "max": 99999, "amount": 0, "count": 0}
    }
    
    # Get sales invoices (unpaid/partial)
    invoice_query = {"status": {"$in": ["unpaid", "partial"]}}
    if branch_id:
        invoice_query["branch_id"] = branch_id
    
    invoices = await db.sales_invoices.find(invoice_query, {"_id": 0}).to_list(10000)
    
    party_aging = {}
    
    for invoice in invoices:
        invoice_date = datetime.fromisoformat(invoice["invoice_date"][:10])
        days_outstanding = (reference_date - invoice_date).days
        
        outstanding = invoice.get("balance_due", invoice.get("grand_total", 0))
        
        if outstanding <= 0:
            continue
        
        # Determine bucket
        bucket_key = None
        for key, bucket in buckets.items():
            if bucket["min"] <= days_outstanding <= bucket["max"]:
                bucket_key = key
                break
        
        if bucket_key:
            buckets[bucket_key]["amount"] += outstanding
            buckets[bucket_key]["count"] += 1
        
        # Track by party
        party_name = invoice.get("customer_name", "Unknown")
        if party_name not in party_aging:
            party_aging[party_name] = {
                "party_name": party_name,
                "0-30": 0, "31-60": 0, "61-90": 0, "91-120": 0, "120+": 0,
                "total": 0
            }
        
        if bucket_key:
            party_aging[party_name][bucket_key] += outstanding
            party_aging[party_name]["total"] += outstanding
    
    # Convert party_aging to list
    parties = list(party_aging.values())
    parties.sort(key=lambda x: x["total"], reverse=True)
    
    return {
        "as_on_date": as_on_date,
        "branch_id": branch_id,
        "summary": buckets,
        "by_party": parties[:50],  # Top 50
        "total_outstanding": sum(b["amount"] for b in buckets.values()),
        "total_parties": len(parties)
    }


@router.get("/aging/payables")
async def get_payables_aging(
    branch_id: Optional[str] = None,
    as_on_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get aging analysis of payables"""
    
    if not as_on_date:
        as_on_date = datetime.now(timezone.utc).isoformat()[:10]
    
    reference_date = datetime.fromisoformat(as_on_date)
    
    buckets = {
        "0-30": {"min": 0, "max": 30, "amount": 0, "count": 0},
        "31-60": {"min": 31, "max": 60, "amount": 0, "count": 0},
        "61-90": {"min": 61, "max": 90, "amount": 0, "count": 0},
        "91-120": {"min": 91, "max": 120, "amount": 0, "count": 0},
        "120+": {"min": 121, "max": 99999, "amount": 0, "count": 0}
    }
    
    # Get purchase invoices (unpaid/partial)
    invoice_query = {"status": {"$in": ["unpaid", "partial"]}}
    if branch_id:
        invoice_query["branch_id"] = branch_id
    
    invoices = await db.purchase_invoices.find(invoice_query, {"_id": 0}).to_list(10000)
    
    party_aging = {}
    
    for invoice in invoices:
        invoice_date = datetime.fromisoformat(invoice.get("invoice_date", invoice.get("entry_date", "2025-01-01"))[:10])
        days_outstanding = (reference_date - invoice_date).days
        
        outstanding = invoice.get("balance_due", invoice.get("grand_total", 0))
        
        if outstanding <= 0:
            continue
        
        bucket_key = None
        for key, bucket in buckets.items():
            if bucket["min"] <= days_outstanding <= bucket["max"]:
                bucket_key = key
                break
        
        if bucket_key:
            buckets[bucket_key]["amount"] += outstanding
            buckets[bucket_key]["count"] += 1
        
        party_name = invoice.get("supplier_name", "Unknown")
        if party_name not in party_aging:
            party_aging[party_name] = {
                "party_name": party_name,
                "0-30": 0, "31-60": 0, "61-90": 0, "91-120": 0, "120+": 0,
                "total": 0
            }
        
        if bucket_key:
            party_aging[party_name][bucket_key] += outstanding
            party_aging[party_name]["total"] += outstanding
    
    parties = list(party_aging.values())
    parties.sort(key=lambda x: x["total"], reverse=True)
    
    return {
        "as_on_date": as_on_date,
        "branch_id": branch_id,
        "summary": buckets,
        "by_party": parties[:50],
        "total_outstanding": sum(b["amount"] for b in buckets.values()),
        "total_parties": len(parties)
    }


# ==================== RATIO ANALYSIS ====================

@router.get("/ratio-analysis")
async def get_ratio_analysis(
    branch_id: Optional[str] = None,
    financial_year: str = "2025-26",
    current_user: dict = Depends(get_current_user)
):
    """Calculate key financial ratios"""
    
    # Determine date range
    fy_parts = financial_year.split("-")
    start_year = int("20" + fy_parts[0]) if len(fy_parts[0]) == 2 else int(fy_parts[0])
    start_date = f"{start_year}-04-01"
    end_date = f"{start_year + 1}-03-31"
    
    # Get account groups
    groups = await db.account_groups.find({}, {"_id": 0}).to_list(1000)
    groups_by_code = {g["code"]: g["id"] for g in groups}
    
    # Get ledgers
    query = {"is_active": True}
    if branch_id:
        query["branch_id"] = branch_id
    
    ledgers = await db.ledgers.find(query, {"_id": 0}).to_list(10000)
    
    # Calculate totals by group
    def get_group_total(group_codes):
        total = 0
        group_ids = [groups_by_code.get(c) for c in group_codes if c in groups_by_code]
        for ledger in ledgers:
            if ledger.get("account_group_id") in group_ids:
                total += abs(ledger.get("current_balance", 0))
        return total
    
    # Calculate key figures
    current_assets = get_group_total(["A01", "A0101", "A0102", "A0103", "A0104", "A0105", "A0106"])
    current_liabilities = get_group_total(["L01", "L0101", "L0102", "L0103", "L0104"])
    fixed_assets = get_group_total(["A02", "A0201", "A0202", "A0203", "A0204", "A0205"])
    total_liabilities = get_group_total(["L01", "L02", "L0101", "L0102", "L0103", "L0104", "L0201", "L0202", "L0203"])
    
    inventory = get_group_total(["A0104"])
    receivables = get_group_total(["A0103"])
    payables = get_group_total(["L0101"])
    cash_bank = get_group_total(["A0101", "A0102"])
    
    sales = get_group_total(["I01", "I0101", "I0102"])
    purchases = get_group_total(["E01", "E0101", "E0102"])
    
    total_assets = current_assets + fixed_assets
    capital = get_group_total(["C01", "C02", "C03"])
    
    # Calculate ratios
    ratios = {}
    
    # Liquidity Ratios
    ratios["current_ratio"] = round(current_assets / current_liabilities, 2) if current_liabilities > 0 else 0
    ratios["quick_ratio"] = round((current_assets - inventory) / current_liabilities, 2) if current_liabilities > 0 else 0
    ratios["cash_ratio"] = round(cash_bank / current_liabilities, 2) if current_liabilities > 0 else 0
    
    # Efficiency Ratios
    ratios["inventory_turnover"] = round(purchases / inventory, 2) if inventory > 0 else 0
    ratios["receivables_turnover"] = round(sales / receivables, 2) if receivables > 0 else 0
    ratios["payables_turnover"] = round(purchases / payables, 2) if payables > 0 else 0
    
    # Days ratios
    ratios["days_inventory"] = round(365 / ratios["inventory_turnover"], 0) if ratios["inventory_turnover"] > 0 else 0
    ratios["days_receivables"] = round(365 / ratios["receivables_turnover"], 0) if ratios["receivables_turnover"] > 0 else 0
    ratios["days_payables"] = round(365 / ratios["payables_turnover"], 0) if ratios["payables_turnover"] > 0 else 0
    
    # Leverage Ratios
    ratios["debt_equity_ratio"] = round(total_liabilities / capital, 2) if capital > 0 else 0
    ratios["debt_ratio"] = round(total_liabilities / total_assets, 2) if total_assets > 0 else 0
    
    # Profitability (need P&L data)
    gross_profit = sales - purchases
    ratios["gross_profit_margin"] = round((gross_profit / sales) * 100, 2) if sales > 0 else 0
    
    return {
        "financial_year": financial_year,
        "branch_id": branch_id,
        "as_on_date": datetime.now(timezone.utc).isoformat()[:10],
        "key_figures": {
            "current_assets": round(current_assets, 2),
            "current_liabilities": round(current_liabilities, 2),
            "fixed_assets": round(fixed_assets, 2),
            "total_assets": round(total_assets, 2),
            "total_liabilities": round(total_liabilities, 2),
            "capital": round(capital, 2),
            "inventory": round(inventory, 2),
            "receivables": round(receivables, 2),
            "payables": round(payables, 2),
            "cash_bank": round(cash_bank, 2),
            "sales": round(sales, 2),
            "purchases": round(purchases, 2)
        },
        "ratios": {
            "liquidity": {
                "current_ratio": {"value": ratios["current_ratio"], "benchmark": "2.0", "interpretation": "Higher is better"},
                "quick_ratio": {"value": ratios["quick_ratio"], "benchmark": "1.0", "interpretation": "Higher is better"},
                "cash_ratio": {"value": ratios["cash_ratio"], "benchmark": "0.5", "interpretation": "Adequate cash"}
            },
            "efficiency": {
                "inventory_turnover": {"value": ratios["inventory_turnover"], "unit": "times", "interpretation": "Higher is better"},
                "receivables_turnover": {"value": ratios["receivables_turnover"], "unit": "times", "interpretation": "Higher is better"},
                "payables_turnover": {"value": ratios["payables_turnover"], "unit": "times", "interpretation": "Lower preserves cash"},
                "days_inventory": {"value": ratios["days_inventory"], "unit": "days", "interpretation": "Lower is better"},
                "days_receivables": {"value": ratios["days_receivables"], "unit": "days", "interpretation": "Lower is better"},
                "days_payables": {"value": ratios["days_payables"], "unit": "days", "interpretation": "Optimize cash flow"}
            },
            "leverage": {
                "debt_equity_ratio": {"value": ratios["debt_equity_ratio"], "benchmark": "<1.5", "interpretation": "Lower is safer"},
                "debt_ratio": {"value": ratios["debt_ratio"], "benchmark": "<0.5", "interpretation": "Lower is safer"}
            },
            "profitability": {
                "gross_profit_margin": {"value": ratios["gross_profit_margin"], "unit": "%", "interpretation": "Higher is better"}
            }
        }
    }


# ==================== SALES ANALYSIS ====================

@router.get("/sales-analysis")
async def get_sales_analysis(
    branch_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    group_by: str = "month",  # month, customer, item, category
    current_user: dict = Depends(get_current_user)
):
    """Sales analysis with various groupings"""
    
    if not start_date:
        start_date = (datetime.now(timezone.utc) - timedelta(days=365)).isoformat()[:10]
    if not end_date:
        end_date = datetime.now(timezone.utc).isoformat()[:10]
    
    query = {"invoice_date": {"$gte": start_date, "$lte": end_date}}
    if branch_id:
        query["branch_id"] = branch_id
    
    invoices = await db.sales_invoices.find(query, {"_id": 0}).to_list(10000)
    
    if group_by == "month":
        analysis = {}
        for inv in invoices:
            month_key = inv["invoice_date"][:7]  # YYYY-MM
            if month_key not in analysis:
                analysis[month_key] = {"month": month_key, "count": 0, "total": 0, "tax": 0}
            analysis[month_key]["count"] += 1
            analysis[month_key]["total"] += inv.get("grand_total", 0)
            analysis[month_key]["tax"] += inv.get("cgst_amount", 0) + inv.get("sgst_amount", 0) + inv.get("igst_amount", 0)
        
        data = sorted(analysis.values(), key=lambda x: x["month"])
    
    elif group_by == "customer":
        analysis = {}
        for inv in invoices:
            customer = inv.get("customer_name", "Unknown")
            if customer not in analysis:
                analysis[customer] = {"customer": customer, "count": 0, "total": 0}
            analysis[customer]["count"] += 1
            analysis[customer]["total"] += inv.get("grand_total", 0)
        
        data = sorted(analysis.values(), key=lambda x: x["total"], reverse=True)[:50]
    
    elif group_by == "item":
        analysis = {}
        for inv in invoices:
            for item in inv.get("items", []):
                item_name = item.get("item_name", "Unknown")
                if item_name not in analysis:
                    analysis[item_name] = {"item": item_name, "quantity": 0, "total": 0}
                analysis[item_name]["quantity"] += item.get("quantity", 0)
                analysis[item_name]["total"] += item.get("amount", 0)
        
        data = sorted(analysis.values(), key=lambda x: x["total"], reverse=True)[:50]
    
    else:
        data = []
    
    total_sales = sum(inv.get("grand_total", 0) for inv in invoices)
    total_invoices = len(invoices)
    
    return {
        "start_date": start_date,
        "end_date": end_date,
        "branch_id": branch_id,
        "group_by": group_by,
        "data": data,
        "summary": {
            "total_sales": round(total_sales, 2),
            "total_invoices": total_invoices,
            "average_invoice": round(total_sales / total_invoices, 2) if total_invoices > 0 else 0
        }
    }


# ==================== PURCHASE ANALYSIS ====================

@router.get("/purchase-analysis")
async def get_purchase_analysis(
    branch_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    group_by: str = "month",
    current_user: dict = Depends(get_current_user)
):
    """Purchase analysis with various groupings"""
    
    if not start_date:
        start_date = (datetime.now(timezone.utc) - timedelta(days=365)).isoformat()[:10]
    if not end_date:
        end_date = datetime.now(timezone.utc).isoformat()[:10]
    
    query = {"entry_date": {"$gte": start_date, "$lte": end_date}}
    if branch_id:
        query["branch_id"] = branch_id
    
    invoices = await db.purchase_invoices.find(query, {"_id": 0}).to_list(10000)
    
    if group_by == "month":
        analysis = {}
        for inv in invoices:
            month_key = inv.get("entry_date", "2025-01")[:7]
            if month_key not in analysis:
                analysis[month_key] = {"month": month_key, "count": 0, "total": 0, "tax": 0}
            analysis[month_key]["count"] += 1
            analysis[month_key]["total"] += inv.get("grand_total", 0)
            analysis[month_key]["tax"] += inv.get("cgst_amount", 0) + inv.get("sgst_amount", 0) + inv.get("igst_amount", 0)
        
        data = sorted(analysis.values(), key=lambda x: x["month"])
    
    elif group_by == "supplier":
        analysis = {}
        for inv in invoices:
            supplier = inv.get("supplier_name", "Unknown")
            if supplier not in analysis:
                analysis[supplier] = {"supplier": supplier, "count": 0, "total": 0}
            analysis[supplier]["count"] += 1
            analysis[supplier]["total"] += inv.get("grand_total", 0)
        
        data = sorted(analysis.values(), key=lambda x: x["total"], reverse=True)[:50]
    
    else:
        data = []
    
    total_purchases = sum(inv.get("grand_total", 0) for inv in invoices)
    total_invoices = len(invoices)
    
    return {
        "start_date": start_date,
        "end_date": end_date,
        "branch_id": branch_id,
        "group_by": group_by,
        "data": data,
        "summary": {
            "total_purchases": round(total_purchases, 2),
            "total_invoices": total_invoices,
            "average_invoice": round(total_purchases / total_invoices, 2) if total_invoices > 0 else 0
        }
    }


# ==================== STOCK VALUATION REPORT ====================

@router.get("/stock-valuation")
async def get_stock_valuation(
    branch_id: Optional[str] = None,
    godown_id: Optional[str] = None,
    as_on_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get stock valuation report (FIFO based)"""
    
    # Get items
    items = await db.items.find({"is_active": True}, {"_id": 0}).to_list(10000)
    items_dict = {i["id"]: i for i in items}
    
    # Get stock batches
    batch_query = {}
    if godown_id:
        batch_query["godown_id"] = godown_id
    
    batches = await db.stock_batches.find(batch_query, {"_id": 0}).to_list(100000)
    
    # Group by item
    item_stocks = {}
    
    for batch in batches:
        item_id = batch["item_id"]
        if item_id not in item_stocks:
            item = items_dict.get(item_id, {})
            item_stocks[item_id] = {
                "item_id": item_id,
                "item_code": item.get("code", ""),
                "item_name": item.get("name", "Unknown"),
                "hsn_code": item.get("hsn_code", ""),
                "unit": item.get("unit", "PCS"),
                "quantity": 0,
                "value": 0,
                "average_cost": 0
            }
        
        qty = batch.get("current_quantity", 0)
        cost = batch.get("cost_price", 0)
        
        item_stocks[item_id]["quantity"] += qty
        item_stocks[item_id]["value"] += qty * cost
    
    # Calculate average cost
    for item in item_stocks.values():
        if item["quantity"] > 0:
            item["average_cost"] = round(item["value"] / item["quantity"], 2)
        item["quantity"] = round(item["quantity"], 2)
        item["value"] = round(item["value"], 2)
    
    stock_items = list(item_stocks.values())
    stock_items.sort(key=lambda x: x["value"], reverse=True)
    
    total_value = sum(i["value"] for i in stock_items)
    total_items = len([i for i in stock_items if i["quantity"] > 0])
    
    return {
        "as_on_date": as_on_date or datetime.now(timezone.utc).isoformat()[:10],
        "branch_id": branch_id,
        "godown_id": godown_id,
        "items": stock_items,
        "summary": {
            "total_value": round(total_value, 2),
            "total_items": total_items,
            "total_skus": len(stock_items)
        }
    }
