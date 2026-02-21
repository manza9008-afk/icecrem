"""
HOOREN ERP - System Administration Routes
Company Settings, Financial Year, Backup/Restore, System Configuration
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.responses import StreamingResponse
from typing import Optional
from datetime import datetime, timezone
import uuid
import json
import io
import gzip

router = APIRouter(prefix="/api/system", tags=["system"])

from server import db
from utils import get_current_user


# ==================== COMPANY SETTINGS ====================

@router.get("/company")
async def get_company_settings(current_user: dict = Depends(get_current_user)):
    """Get company settings"""
    company = await db.company_settings.find_one({}, {"_id": 0})
    
    if not company:
        # Create default settings
        company = {
            "id": str(uuid.uuid4()),
            "name": "HOOREN FOOD PRODUCTS",
            "legal_name": "HOOREN FOOD PRODUCTS PRIVATE LIMITED",
            "address": "Survey No 409, Ranuj",
            "city": "Patan",
            "state": "Gujarat",
            "state_code": "24",
            "pin_code": "384265",
            "country": "India",
            "phone": "",
            "email": "",
            "website": "",
            "gstin": "24AAHFH1702M1ZK",
            "pan": "AAHFH1702M",
            "cin": "",
            "tan": "",
            "bank_name": "State Bank of India",
            "bank_account": "",
            "bank_ifsc": "",
            "bank_branch": "",
            "upi_id": "",
            "logo_url": "",
            "signature_url": "",
            "invoice_prefix": "INV",
            "invoice_terms": "1. Goods once sold will not be taken back\n2. Subject to Gujarat Jurisdiction",
            "default_credit_days": 30,
            "financial_year_start_month": 4,
            "currency": "INR",
            "currency_symbol": "₹",
            "decimal_places": 2,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.company_settings.insert_one(company)
        company.pop("_id", None)
    
    return company


@router.put("/company")
async def update_company_settings(
    settings: dict,
    current_user: dict = Depends(get_current_user)
):
    """Update company settings"""
    existing = await db.company_settings.find_one({})
    
    if not existing:
        raise HTTPException(status_code=404, detail="Company settings not found")
    
    settings["modified_at"] = datetime.now(timezone.utc).isoformat()
    settings["modified_by"] = current_user["username"]
    
    await db.company_settings.update_one({}, {"$set": settings})
    
    return {"message": "Company settings updated"}


# ==================== FINANCIAL YEAR ====================

@router.get("/financial-years")
async def get_financial_years(current_user: dict = Depends(get_current_user)):
    """Get all financial years"""
    years = await db.financial_years.find({}, {"_id": 0}).sort("start_date", -1).to_list(100)
    
    if not years:
        # Create current financial year
        current_year = {
            "id": str(uuid.uuid4()),
            "code": "2025-26",
            "name": "Financial Year 2025-26",
            "start_date": "2025-04-01",
            "end_date": "2026-03-31",
            "is_active": True,
            "is_locked": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.financial_years.insert_one(current_year)
        years = [current_year]
    
    return years


@router.get("/financial-years/current")
async def get_current_financial_year(current_user: dict = Depends(get_current_user)):
    """Get current active financial year"""
    fy = await db.financial_years.find_one({"is_active": True}, {"_id": 0})
    
    if not fy:
        raise HTTPException(status_code=404, detail="No active financial year found")
    
    return fy


@router.post("/financial-years")
async def create_financial_year(
    fy_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Create a new financial year"""
    
    # Check code uniqueness
    existing = await db.financial_years.find_one({"code": fy_data["code"]})
    if existing:
        raise HTTPException(status_code=400, detail="Financial year code already exists")
    
    fy_doc = {
        "id": str(uuid.uuid4()),
        **fy_data,
        "is_active": False,
        "is_locked": False,
        "created_by": current_user["username"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.financial_years.insert_one(fy_doc)
    fy_doc.pop("_id", None)
    
    return fy_doc


@router.put("/financial-years/{fy_id}/activate")
async def activate_financial_year(
    fy_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Activate a financial year (deactivates others)"""
    fy = await db.financial_years.find_one({"id": fy_id})
    if not fy:
        raise HTTPException(status_code=404, detail="Financial year not found")
    
    # Deactivate all
    await db.financial_years.update_many({}, {"$set": {"is_active": False}})
    
    # Activate selected
    await db.financial_years.update_one(
        {"id": fy_id},
        {"$set": {
            "is_active": True,
            "activated_at": datetime.now(timezone.utc).isoformat(),
            "activated_by": current_user["username"]
        }}
    )
    
    return {"message": f"Financial Year {fy['code']} activated"}


@router.put("/financial-years/{fy_id}/lock")
async def lock_financial_year(
    fy_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Lock a financial year (prevents modifications)"""
    fy = await db.financial_years.find_one({"id": fy_id})
    if not fy:
        raise HTTPException(status_code=404, detail="Financial year not found")
    
    await db.financial_years.update_one(
        {"id": fy_id},
        {"$set": {
            "is_locked": True,
            "locked_at": datetime.now(timezone.utc).isoformat(),
            "locked_by": current_user["username"]
        }}
    )
    
    return {"message": f"Financial Year {fy['code']} locked"}


# ==================== BACKUP & RESTORE ====================

@router.get("/backup")
async def create_backup(
    include_settings: bool = True,
    include_masters: bool = True,
    include_transactions: bool = True,
    current_user: dict = Depends(get_current_user)
):
    """Create a full database backup"""
    
    backup_data = {
        "backup_info": {
            "version": "1.0",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "created_by": current_user["username"],
            "includes": {
                "settings": include_settings,
                "masters": include_masters,
                "transactions": include_transactions
            }
        }
    }
    
    if include_settings:
        backup_data["company_settings"] = await db.company_settings.find({}, {"_id": 0}).to_list(10)
        backup_data["financial_years"] = await db.financial_years.find({}, {"_id": 0}).to_list(100)
        backup_data["roles"] = await db.roles.find({}, {"_id": 0}).to_list(100)
        backup_data["users"] = await db.users.find({}, {"_id": 0, "password": 0}).to_list(1000)
    
    if include_masters:
        backup_data["branches"] = await db.branches.find({}, {"_id": 0}).to_list(1000)
        backup_data["godowns"] = await db.godowns.find({}, {"_id": 0}).to_list(1000)
        backup_data["account_groups"] = await db.account_groups.find({}, {"_id": 0}).to_list(1000)
        backup_data["ledgers"] = await db.ledgers.find({}, {"_id": 0}).to_list(100000)
        backup_data["items"] = await db.items.find({}, {"_id": 0}).to_list(100000)
        backup_data["customers"] = await db.customers.find({}, {"_id": 0}).to_list(100000)
        backup_data["suppliers"] = await db.suppliers.find({}, {"_id": 0}).to_list(100000)
        backup_data["hsn_codes"] = await db.hsn_codes.find({}, {"_id": 0}).to_list(10000)
    
    if include_transactions:
        backup_data["vouchers"] = await db.vouchers.find({}, {"_id": 0}).to_list(1000000)
        backup_data["ledger_transactions"] = await db.ledger_transactions.find({}, {"_id": 0}).to_list(1000000)
        backup_data["sales_invoices"] = await db.sales_invoices.find({}, {"_id": 0}).to_list(1000000)
        backup_data["purchase_invoices"] = await db.purchase_invoices.find({}, {"_id": 0}).to_list(1000000)
        backup_data["sales_quotations"] = await db.sales_quotations.find({}, {"_id": 0}).to_list(100000)
        backup_data["sales_orders"] = await db.sales_orders.find({}, {"_id": 0}).to_list(100000)
        backup_data["purchase_orders"] = await db.purchase_orders.find({}, {"_id": 0}).to_list(100000)
        backup_data["stock_batches"] = await db.stock_batches.find({}, {"_id": 0}).to_list(1000000)
        backup_data["stock_transactions"] = await db.stock_transactions.find({}, {"_id": 0}).to_list(1000000)
    
    # Compress the backup
    json_data = json.dumps(backup_data, indent=2, default=str)
    compressed = gzip.compress(json_data.encode('utf-8'))
    
    # Create filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"hooren_erp_backup_{timestamp}.json.gz"
    
    return StreamingResponse(
        io.BytesIO(compressed),
        media_type="application/gzip",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.post("/restore")
async def restore_backup(
    file: UploadFile = File(...),
    restore_settings: bool = True,
    restore_masters: bool = True,
    restore_transactions: bool = True,
    current_user: dict = Depends(get_current_user)
):
    """Restore database from backup"""
    
    try:
        content = await file.read()
        
        # Decompress if gzipped
        if file.filename.endswith('.gz'):
            content = gzip.decompress(content)
        
        backup_data = json.loads(content.decode('utf-8'))
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid backup file: {str(e)}")
    
    # Verify backup format
    if "backup_info" not in backup_data:
        raise HTTPException(status_code=400, detail="Invalid backup format")
    
    restored_collections = []
    
    try:
        if restore_settings and backup_data.get("company_settings"):
            await db.company_settings.delete_many({})
            if backup_data["company_settings"]:
                await db.company_settings.insert_many(backup_data["company_settings"])
            restored_collections.append("company_settings")
        
        if restore_settings and backup_data.get("financial_years"):
            await db.financial_years.delete_many({})
            if backup_data["financial_years"]:
                await db.financial_years.insert_many(backup_data["financial_years"])
            restored_collections.append("financial_years")
        
        if restore_masters and backup_data.get("account_groups"):
            await db.account_groups.delete_many({})
            if backup_data["account_groups"]:
                await db.account_groups.insert_many(backup_data["account_groups"])
            restored_collections.append("account_groups")
        
        if restore_masters and backup_data.get("ledgers"):
            await db.ledgers.delete_many({})
            if backup_data["ledgers"]:
                await db.ledgers.insert_many(backup_data["ledgers"])
            restored_collections.append("ledgers")
        
        if restore_masters and backup_data.get("items"):
            await db.items.delete_many({})
            if backup_data["items"]:
                await db.items.insert_many(backup_data["items"])
            restored_collections.append("items")
        
        if restore_transactions and backup_data.get("vouchers"):
            await db.vouchers.delete_many({})
            if backup_data["vouchers"]:
                await db.vouchers.insert_many(backup_data["vouchers"])
            restored_collections.append("vouchers")
        
        if restore_transactions and backup_data.get("ledger_transactions"):
            await db.ledger_transactions.delete_many({})
            if backup_data["ledger_transactions"]:
                await db.ledger_transactions.insert_many(backup_data["ledger_transactions"])
            restored_collections.append("ledger_transactions")
        
        if restore_transactions and backup_data.get("sales_invoices"):
            await db.sales_invoices.delete_many({})
            if backup_data["sales_invoices"]:
                await db.sales_invoices.insert_many(backup_data["sales_invoices"])
            restored_collections.append("sales_invoices")
        
        if restore_transactions and backup_data.get("stock_batches"):
            await db.stock_batches.delete_many({})
            if backup_data["stock_batches"]:
                await db.stock_batches.insert_many(backup_data["stock_batches"])
            restored_collections.append("stock_batches")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Restore failed: {str(e)}")
    
    # Log the restore action
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "SYSTEM_RESTORE",
        "entity_type": "backup",
        "entity_id": backup_data["backup_info"].get("created_at", ""),
        "old_data": None,
        "new_data": {"restored_collections": restored_collections},
        "username": current_user["username"],
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "message": "Backup restored successfully",
        "restored_collections": restored_collections,
        "backup_created_at": backup_data["backup_info"].get("created_at")
    }


# ==================== SYSTEM STATS ====================

@router.get("/stats")
async def get_system_stats(current_user: dict = Depends(get_current_user)):
    """Get system statistics"""
    
    stats = {
        "database": {},
        "transactions": {},
        "storage": {}
    }
    
    # Collection counts
    stats["database"]["branches"] = await db.branches.count_documents({})
    stats["database"]["ledgers"] = await db.ledgers.count_documents({})
    stats["database"]["items"] = await db.items.count_documents({})
    stats["database"]["customers"] = await db.customers.count_documents({})
    stats["database"]["suppliers"] = await db.suppliers.count_documents({})
    
    stats["transactions"]["vouchers"] = await db.vouchers.count_documents({})
    stats["transactions"]["sales_invoices"] = await db.sales_invoices.count_documents({})
    stats["transactions"]["purchase_invoices"] = await db.purchase_invoices.count_documents({})
    stats["transactions"]["stock_transactions"] = await db.stock_transactions.count_documents({})
    
    # Get database stats
    try:
        db_stats = await db.command("dbStats")
        stats["storage"]["data_size_mb"] = round(db_stats.get("dataSize", 0) / (1024 * 1024), 2)
        stats["storage"]["index_size_mb"] = round(db_stats.get("indexSize", 0) / (1024 * 1024), 2)
        stats["storage"]["total_size_mb"] = round(db_stats.get("storageSize", 0) / (1024 * 1024), 2)
    except:
        stats["storage"]["data_size_mb"] = 0
        stats["storage"]["index_size_mb"] = 0
        stats["storage"]["total_size_mb"] = 0
    
    return stats


# ==================== SYSTEM CONFIGURATION ====================

@router.get("/config")
async def get_system_config(current_user: dict = Depends(get_current_user)):
    """Get system configuration"""
    
    config = await db.system_config.find_one({}, {"_id": 0})
    
    if not config:
        config = {
            "id": str(uuid.uuid4()),
            "voucher_numbering": {
                "auto_generate": True,
                "prefix_with_branch": True,
                "prefix_with_fy": True,
                "reset_on_fy": True
            },
            "stock_settings": {
                "valuation_method": "FIFO",
                "allow_negative_stock": False,
                "track_batch_expiry": True,
                "expiry_warning_days": 30
            },
            "gst_settings": {
                "company_gstin": "24AAHFH1702M1ZK",
                "default_tax_type": "intra",
                "enable_eway_bill": False,
                "enable_e_invoice": False
            },
            "invoice_settings": {
                "auto_generate_number": True,
                "show_hsn": True,
                "show_discount": True,
                "show_transport": True,
                "default_payment_terms": 30
            },
            "report_settings": {
                "default_date_range": "current_month",
                "show_zero_balance": False,
                "group_by_account_type": True
            },
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.system_config.insert_one(config)
        config.pop("_id", None)
    
    return config


@router.put("/config")
async def update_system_config(
    config: dict,
    current_user: dict = Depends(get_current_user)
):
    """Update system configuration"""
    
    existing = await db.system_config.find_one({})
    
    if existing:
        config["modified_at"] = datetime.now(timezone.utc).isoformat()
        config["modified_by"] = current_user["username"]
        await db.system_config.update_one({}, {"$set": config})
    else:
        config["id"] = str(uuid.uuid4())
        config["created_at"] = datetime.now(timezone.utc).isoformat()
        await db.system_config.insert_one(config)
    
    return {"message": "System configuration updated"}


# ==================== DATABASE OPTIMIZATION ====================

@router.post("/optimize")
async def optimize_database(current_user: dict = Depends(get_current_user)):
    """Optimize database indexes and performance"""
    
    optimizations = []
    
    # Create indexes
    indexes_to_create = [
        ("ledgers", [("branch_id", 1), ("account_group_id", 1)]),
        ("ledgers", [("is_active", 1)]),
        ("vouchers", [("branch_id", 1), ("voucher_date", -1)]),
        ("vouchers", [("voucher_type", 1), ("status", 1)]),
        ("ledger_transactions", [("ledger_id", 1), ("voucher_date", 1)]),
        ("sales_invoices", [("branch_id", 1), ("invoice_date", -1)]),
        ("sales_invoices", [("customer_name", 1)]),
        ("purchase_invoices", [("branch_id", 1), ("entry_date", -1)]),
        ("stock_batches", [("item_id", 1), ("godown_id", 1)]),
        ("stock_batches", [("expiry_date", 1)]),
        ("items", [("code", 1)], {"unique": True}),
        ("items", [("hsn_code", 1)]),
        ("audit_logs", [("entity_type", 1), ("entity_id", 1)]),
        ("audit_logs", [("created_at", -1)]),
    ]
    
    for collection_name, index_keys, *options in indexes_to_create:
        try:
            collection = db[collection_name]
            opts = options[0] if options else {}
            await collection.create_index(index_keys, **opts)
            optimizations.append(f"Created index on {collection_name}: {index_keys}")
        except Exception as e:
            optimizations.append(f"Index on {collection_name} already exists or error: {str(e)}")
    
    return {
        "message": "Database optimization complete",
        "optimizations": optimizations
    }
