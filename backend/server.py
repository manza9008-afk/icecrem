"""
HOOREN FOOD PRODUCTS ERP - Main Server
Complete Multi-Branch ERP System
"""
from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt
import io

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Settings
SECRET_KEY = os.getenv("SECRET_KEY", "hooren-erp-secret-key-2025-secure")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480

# Create the main app
app = FastAPI(
    title="HOOREN FOOD PRODUCTS ERP",
    description="Complete Multi-Branch ERP System with GST Compliance",
    version="1.0.0"
)

api_router = APIRouter(prefix="/api")
security = HTTPBearer()


# ==================== UTILITIES ====================

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return {"username": username}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid credentials")


# ==================== MODELS ====================

class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict


class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str


# ==================== AUTHENTICATION ====================

@api_router.post("/auth/login", response_model=LoginResponse)
async def login(credentials: LoginRequest):
    user = await db.users.find_one({"username": credentials.username}, {"_id": 0})
    
    if not user or not pwd_context.verify(credentials.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    await db.users.update_one(
        {"username": credentials.username},
        {"$set": {"last_login": datetime.now(timezone.utc).isoformat()}}
    )
    
    access_token = create_access_token(data={"sub": user["username"]})
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user={
            "username": user["username"],
            "email": user["email"],
            "full_name": user["full_name"],
            "require_password_change": user.get("require_password_change", False)
        }
    )


@api_router.post("/auth/change-password")
async def change_password(request: PasswordChangeRequest, current_user: dict = Depends(get_current_user)):
    user = await db.users.find_one({"username": current_user["username"]})
    
    if not pwd_context.verify(request.old_password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Invalid old password")
    
    new_hash = pwd_context.hash(request.new_password)
    await db.users.update_one(
        {"username": current_user["username"]},
        {"$set": {"password_hash": new_hash, "require_password_change": False}}
    )
    
    return {"message": "Password changed successfully"}


@api_router.get("/auth/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    user = await db.users.find_one({"username": current_user["username"]}, {"_id": 0, "password_hash": 0})
    return user


# ==================== DASHBOARD ====================

@api_router.get("/dashboard/stats")
async def get_dashboard_stats(
    branch_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = today_start.replace(day=1)
    
    # Build query
    sales_query = {"status": "completed"}
    if branch_id:
        sales_query["branch_id"] = branch_id
    
    # Today's sales
    today_query = {**sales_query, "invoice_date": {"$gte": today_start.isoformat()[:10]}}
    sales_today = await db.sales_invoices.aggregate([
        {"$match": today_query},
        {"$group": {"_id": None, "total": {"$sum": "$grand_total"}}}
    ]).to_list(1)
    
    # Monthly sales
    month_query = {**sales_query, "invoice_date": {"$gte": month_start.isoformat()[:10]}}
    sales_month = await db.sales_invoices.aggregate([
        {"$match": month_query},
        {"$group": {"_id": None, "total": {"$sum": "$grand_total"}}}
    ]).to_list(1)
    
    # Low stock items
    low_stock_count = await db.stock_batches.count_documents({
        "remaining_quantity": {"$gt": 0, "$lt": 10},
        "is_active": True
    })
    
    # Outstanding receivables
    ledger_query = {"is_party": True, "is_active": True}
    if branch_id:
        ledger_query["branch_id"] = branch_id
    
    debtors_group = await db.account_groups.find_one({"code": "A0103"})
    if debtors_group:
        ledger_query["account_group_id"] = debtors_group["id"]
        ledgers = await db.ledgers.find(ledger_query, {"_id": 0}).to_list(10000)
        outstanding = sum(l.get("current_balance", 0) for l in ledgers if l.get("current_balance", 0) > 0)
    else:
        outstanding = 0
    
    # Pending orders count
    pending_orders = await db.sales_orders.count_documents({"status": {"$in": ["pending", "partial"]}})
    
    # Today's purchases
    purchase_today = await db.purchase_invoices.aggregate([
        {"$match": {"invoice_date": {"$gte": today_start.isoformat()[:10]}, "status": "completed"}},
        {"$group": {"_id": None, "total": {"$sum": "$grand_total"}}}
    ]).to_list(1)
    
    return {
        "today_sales": sales_today[0]["total"] if sales_today else 0,
        "monthly_sales": sales_month[0]["total"] if sales_month else 0,
        "today_purchases": purchase_today[0]["total"] if purchase_today else 0,
        "low_stock_items": low_stock_count,
        "outstanding_receivables": outstanding,
        "pending_orders": pending_orders
    }


@api_router.get("/dashboard/recent-activity")
async def get_recent_activity(
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
):
    activities = []
    
    # Recent sales
    sales = await db.sales_invoices.find(
        {"status": "completed"}, {"_id": 0}
    ).sort("created_at", -1).limit(5).to_list(5)
    
    for sale in sales:
        activities.append({
            "type": "sales",
            "description": f"Sales Invoice {sale['invoice_number']} - {sale['customer_name']}",
            "amount": sale["grand_total"],
            "date": sale["created_at"]
        })
    
    # Recent purchases
    purchases = await db.purchase_invoices.find(
        {"status": "completed"}, {"_id": 0}
    ).sort("created_at", -1).limit(5).to_list(5)
    
    for purchase in purchases:
        activities.append({
            "type": "purchase",
            "description": f"Purchase Invoice {purchase['invoice_number']} - {purchase['supplier_name']}",
            "amount": purchase["grand_total"],
            "date": purchase["created_at"]
        })
    
    # Sort by date
    activities.sort(key=lambda x: x["date"], reverse=True)
    
    return activities[:limit]


# ==================== COMPANY SETTINGS ====================

@api_router.get("/settings/company")
async def get_company_settings(current_user: dict = Depends(get_current_user)):
    settings = await db.company_settings.find_one({}, {"_id": 0})
    return settings or {}


@api_router.put("/settings/company")
async def update_company_settings(settings: dict, current_user: dict = Depends(get_current_user)):
    settings["modified_at"] = datetime.now(timezone.utc).isoformat()
    await db.company_settings.update_one({}, {"$set": settings}, upsert=True)
    return {"message": "Settings updated successfully"}


# ==================== CUSTOMERS ====================

@api_router.get("/customers")
async def get_customers(
    search: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    query = {"is_active": True}
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"gstin": {"$regex": search, "$options": "i"}}
        ]
    
    customers = await db.customers.find(query, {"_id": 0}).to_list(10000)
    return customers


@api_router.post("/customers")
async def create_customer(customer_data: dict, current_user: dict = Depends(get_current_user)):
    customer_doc = {
        "id": str(uuid.uuid4()),
        **customer_data,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.customers.insert_one(customer_doc)
    customer_doc.pop("_id", None)
    return customer_doc


@api_router.put("/customers/{customer_id}")
async def update_customer(
    customer_id: str,
    customer_data: dict,
    current_user: dict = Depends(get_current_user)
):
    result = await db.customers.update_one({"id": customer_id}, {"$set": customer_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Customer not found")
    return {"message": "Customer updated"}


# ==================== SUPPLIERS ====================

@api_router.get("/suppliers")
async def get_suppliers(
    search: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    query = {"is_active": True}
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"gstin": {"$regex": search, "$options": "i"}}
        ]
    
    suppliers = await db.suppliers.find(query, {"_id": 0}).to_list(10000)
    return suppliers


@api_router.post("/suppliers")
async def create_supplier(supplier_data: dict, current_user: dict = Depends(get_current_user)):
    supplier_doc = {
        "id": str(uuid.uuid4()),
        **supplier_data,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.suppliers.insert_one(supplier_doc)
    supplier_doc.pop("_id", None)
    return supplier_doc


@api_router.put("/suppliers/{supplier_id}")
async def update_supplier(
    supplier_id: str,
    supplier_data: dict,
    current_user: dict = Depends(get_current_user)
):
    result = await db.suppliers.update_one({"id": supplier_id}, {"$set": supplier_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return {"message": "Supplier updated"}


# ==================== HEALTH CHECK ====================

@api_router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0"
    }


# Include main API router
app.include_router(api_router)

# Include module routers
from routes.branch_routes import router as branch_router
from routes.accounting_routes import router as accounting_router
from routes.inventory_routes import router as inventory_router
from routes.sales_routes import router as sales_router
from routes.purchase_routes import router as purchase_router
from routes.gst_routes import router as gst_router
from routes.security_routes import router as security_router
from routes.advanced_reports_routes import router as advanced_reports_router
from routes.pdf_routes import router as pdf_router
from routes.system_routes import router as system_router

app.include_router(branch_router)
app.include_router(accounting_router)
app.include_router(inventory_router)
app.include_router(sales_router)
app.include_router(purchase_router)
app.include_router(gst_router)
app.include_router(security_router)
app.include_router(advanced_reports_router)
app.include_router(pdf_router)
app.include_router(system_router)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@app.on_event("startup")
async def startup_db():
    """Initialize database with required data"""
    
    # Create default admin user
    admin = await db.users.find_one({"username": "hooren_admin"})
    if not admin:
        admin_user = {
            "username": "hooren_admin",
            "password_hash": pwd_context.hash("Hooren@2026#Secure"),
            "email": "maanzaicecream@gmail.com",
            "full_name": "Admin User",
            "require_password_change": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.users.insert_one(admin_user)
        logger.info("Created admin user")
    
    # Initialize company settings
    settings = await db.company_settings.find_one({})
    if not settings:
        company_data = {
            "business_name": "HOOREN FOOD PRODUCTS",
            "trade_name": "HOOREN FOOD PRODUCT",
            "gstin": "24AAHFH1702M1ZK",
            "pan": "AAHFH1702M",
            "address": "Survey No 409, R.S. No 409, At Ranuj, Post Ranuj, Taluka Patan",
            "city": "Patan",
            "state": "Gujarat",
            "state_code": "24",
            "pincode": "384275",
            "phone": "9725368208",
            "email": "maanzaicecream@gmail.com",
            "bank_name": "Kotak Mahindra Bank",
            "account_number": "0711473537",
            "ifsc": "KKBK0000848",
            "branch": "Siddhpur",
            "financial_year": "2025-26"
        }
        await db.company_settings.insert_one(company_data)
        logger.info("Created company settings")
    
    # Create default branch if none exists
    branch_count = await db.branches.count_documents({})
    if branch_count == 0:
        default_branch = {
            "id": str(uuid.uuid4()),
            "code": "HO",
            "name": "Head Office - Patan",
            "address": "Survey No 409, R.S. No 409, At Ranuj, Post Ranuj, Taluka Patan",
            "city": "Patan",
            "state": "Gujarat",
            "state_code": "24",
            "pincode": "384275",
            "gstin": "24AAHFH1702M1ZK",
            "phone": "9725368208",
            "email": "maanzaicecream@gmail.com",
            "is_head_office": True,
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.branches.insert_one(default_branch)
        
        # Create default godown
        default_godown = {
            "id": str(uuid.uuid4()),
            "code": "HO-MAIN",
            "name": "Main Godown",
            "branch_id": default_branch["id"],
            "address": default_branch["address"],
            "is_default": True,
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.godowns.insert_one(default_godown)
        
        # Seed Chart of Accounts
        from services.accounting_service import seed_chart_of_accounts
        await seed_chart_of_accounts(db, default_branch["id"])
        
        logger.info("Created default branch, godown, and chart of accounts")
    
    # Seed HSN codes
    hsn_count = await db.hsn_master.count_documents({})
    if hsn_count == 0:
        from routes.gst_routes import seed_hsn_data
        # We'll handle this manually since route depends on user
        hsn_codes = [
            {"hsn_code": "2105", "description": "Ice cream and other edible ice", "gst_rate": 18},
            {"hsn_code": "0401", "description": "Milk and cream, not concentrated", "gst_rate": 0},
            {"hsn_code": "0402", "description": "Milk and cream, concentrated", "gst_rate": 5},
            {"hsn_code": "0405", "description": "Butter and fats from milk", "gst_rate": 12},
            {"hsn_code": "1806", "description": "Chocolate preparations", "gst_rate": 18},
            {"hsn_code": "2106", "description": "Food preparations NES", "gst_rate": 18},
        ]
        for hsn in hsn_codes:
            hsn_doc = {
                "id": str(uuid.uuid4()),
                **hsn,
                "cess_rate": 0,
                "is_active": True,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.hsn_master.insert_one(hsn_doc)
        logger.info("Seeded HSN codes")
    
    # Create indexes for performance
    await db.vouchers.create_index([("voucher_date", -1)])
    await db.vouchers.create_index([("voucher_type", 1), ("branch_id", 1)])
    await db.ledger_transactions.create_index([("ledger_id", 1), ("voucher_date", 1)])
    await db.sales_invoices.create_index([("invoice_date", -1)])
    await db.sales_invoices.create_index([("branch_id", 1), ("invoice_type", 1)])
    await db.purchase_invoices.create_index([("invoice_date", -1)])
    await db.stock_batches.create_index([("item_id", 1), ("branch_id", 1), ("godown_id", 1)])
    await db.stock_transactions.create_index([("item_id", 1), ("transaction_date", -1)])
    
    logger.info("Database indexes created")


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
