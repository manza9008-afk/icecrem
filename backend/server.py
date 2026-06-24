"""
HOOREN FOOD PRODUCTS ERP - Main Server
Complete Multi-Branch ERP System
"""
from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
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

from sqlalchemy.future import select
from sqlalchemy import func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from database import engine, SessionLocal, Base, get_db, init_db
from db_models import User, CompanySettings, Branch, Godown, Customer, Supplier, HSNMaster
from legacy_pg import PostgresDocumentStore

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Older document-style routes store their data in PostgreSQL as JSON rows.
db = PostgresDocumentStore(SessionLocal)

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

def to_dict(obj):
    if not obj: return {}
    result = {}
    for c in obj.__table__.columns:
        val = getattr(obj, c.name)
        if hasattr(val, 'isoformat'):
            val = val.isoformat()
        result[c.name] = val
    return result

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
async def login(credentials: LoginRequest, session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(User).where(User.username == credentials.username))
    user = result.scalar_one_or_none()
    
    if not user or not pwd_context.verify(credentials.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    user.last_login = datetime.now(timezone.utc)
    await session.commit()
    
    access_token = create_access_token(data={"sub": user.username})
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user={
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "require_password_change": user.require_password_change
        }
    )


@api_router.post("/auth/change-password")
async def change_password(request: PasswordChangeRequest, current_user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(User).where(User.username == current_user["username"]))
    user = result.scalar_one_or_none()
    
    if not pwd_context.verify(request.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid old password")
    
    user.password_hash = pwd_context.hash(request.new_password)
    user.require_password_change = False
    await session.commit()
    
    return {"message": "Password changed successfully"}


@api_router.get("/auth/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(User).where(User.username == current_user["username"]))
    user = result.scalar_one_or_none()
    user_dict = to_dict(user)
    user_dict.pop("password_hash", None)
    return user_dict


# ==================== DASHBOARD ====================

@api_router.get("/dashboard/stats")
async def get_dashboard_stats(
    branch_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    # NOTE: Pending migration of full ORM models to calculate actual dashboard stats
    return {
        "today_sales": 0,
        "monthly_sales": 0,
        "today_purchases": 0,
        "low_stock_items": 0,
        "outstanding_receivables": 0,
        "pending_orders": 0
    }


@api_router.get("/dashboard/recent-activity")
async def get_recent_activity(
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
):
    # NOTE: Pending migration to PostgreSQL
    return []


# ==================== COMPANY SETTINGS ====================

@api_router.get("/settings/company")
async def get_company_settings(current_user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(CompanySettings))
    settings = result.scalar_one_or_none()
    return to_dict(settings) if settings else {}


@api_router.put("/settings/company")
async def update_company_settings(settings: dict, current_user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(CompanySettings))
    comp = result.scalar_one_or_none()
    if comp:
        for key, val in settings.items():
            setattr(comp, key, val)
    else:
        comp = CompanySettings(**settings)
        session.add(comp)
    await session.commit()
    return {"message": "Settings updated successfully"}


# ==================== CUSTOMERS ====================

@api_router.get("/customers")
async def get_customers(
    search: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    query = select(Customer).where(Customer.is_active == True)
    if search:
        query = query.where((Customer.name.ilike(f"%{search}%")) | (Customer.gstin.ilike(f"%{search}%")))
    result = await session.execute(query)
    customers = result.scalars().all()
    return [to_dict(c) for c in customers]


@api_router.post("/customers")
async def create_customer(customer_data: dict, current_user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    new_customer = Customer(id=str(uuid.uuid4()), **customer_data, is_active=True, created_at=datetime.now(timezone.utc))
    session.add(new_customer)
    await session.commit()
    return to_dict(new_customer)


@api_router.put("/customers/{customer_id}")
async def update_customer(
    customer_id: str,
    customer_data: dict,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    result = await session.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    for key, value in customer_data.items():
        setattr(customer, key, value)
    await session.commit()
    return {"message": "Customer updated"}


# ==================== SUPPLIERS ====================

@api_router.get("/suppliers")
async def get_suppliers(
    search: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    query = select(Supplier).where(Supplier.is_active == True)
    if search:
        query = query.where((Supplier.name.ilike(f"%{search}%")) | (Supplier.gstin.ilike(f"%{search}%")))
    result = await session.execute(query)
    suppliers = result.scalars().all()
    return [to_dict(s) for s in suppliers]


@api_router.post("/suppliers")
async def create_supplier(supplier_data: dict, current_user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    new_supplier = Supplier(id=str(uuid.uuid4()), **supplier_data, is_active=True, created_at=datetime.now(timezone.utc))
    session.add(new_supplier)
    await session.commit()
    return to_dict(new_supplier)


@api_router.put("/suppliers/{supplier_id}")
async def update_supplier(
    supplier_id: str,
    supplier_data: dict,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    result = await session.execute(select(Supplier).where(Supplier.id == supplier_id))
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    for key, value in supplier_data.items():
        setattr(supplier, key, value)
    await session.commit()
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
from routes_accounting import router as accounting_router
from routes_vouchers import router as voucher_router
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
app.include_router(voucher_router)
app.include_router(inventory_router)
app.include_router(sales_router)
app.include_router(purchase_router)
app.include_router(gst_router)
app.include_router(security_router)
app.include_router(advanced_reports_router)
app.include_router(pdf_router)
app.include_router(system_router)

def get_cors_origins() -> List[str]:
    raw_origins = [origin.strip() for origin in os.environ.get("CORS_ORIGINS", "*").split(",") if origin.strip()]
    if not raw_origins or "*" in raw_origins:
        return ["*"]

    origins = set(raw_origins)
    dev_loopback_origins = {
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    }

    if any(origin in dev_loopback_origins for origin in raw_origins):
        origins.update(dev_loopback_origins)

    return sorted(origins)


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=get_cors_origins(),
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
    """Initialize database with required data (migrated to PostgreSQL/SQLAlchemy)"""
    await init_db()
    async with SessionLocal() as session:
        # ---- Create default admin user ----
        result = await session.execute(select(User).where(User.username == "hooren_admin"))
        admin = result.scalar_one_or_none()
        if not admin:
            admin_user = User(
                id=str(uuid.uuid4()),
                username="hooren_admin",
                password_hash=pwd_context.hash("Hooren@2026#Secure"),
                email="maanzaicecream@gmail.com",
                full_name="Admin User",
                require_password_change=True,
                created_at=datetime.now(timezone.utc)
            )
            session.add(admin_user)
            await session.commit()
            logger.info("Created admin user")

        # ---- Initialize company settings ----
        result = await session.execute(select(CompanySettings))
        settings = result.scalar_one_or_none()
        if not settings:
            company = CompanySettings(
                id=str(uuid.uuid4()),
                business_name="HOOREN FOOD PRODUCTS",
                trade_name="HOOREN FOOD PRODUCT",
                gstin="24AAHFH1702M1ZK",
                pan="AAHFH1702M",
                address="Survey No 409, R.S. No 409, At Ranuj, Post Ranuj, Taluka Patan",
                city="Patan",
                state="Gujarat",
                state_code="24",
                pincode="384275",
                phone="9725368208",
                email="maanzaicecream@gmail.com",
                bank_name="Kotak Mahindra Bank",
                account_number="0711473537",
                ifsc="KKBK0000848",
                branch="Siddhpur",
                financial_year="2025-26"
            )
            session.add(company)
            await session.commit()
            logger.info("Created company settings")

        # ---- Create default branch + godowns if none exist ----
        result = await session.execute(select(Branch))
        existing_branch = result.scalars().first()
        if not existing_branch:
            default_branch = Branch(
                id=str(uuid.uuid4()),
                code="HO",
                name="Head Office - Patan",
                address="Survey No 409, R.S. No 409, At Ranuj, Post Ranuj, Taluka Patan",
                city="Patan",
                state="Gujarat",
                state_code="24",
                pincode="384275",
                gstin="24AAHFH1702M1ZK",
                phone="9725368208",
                email="maanzaicecream@gmail.com",
                is_head_office=True,
                is_active=True,
                created_at=datetime.now(timezone.utc)
            )
            session.add(default_branch)
            await session.flush()  # ensures default_branch.id is available below

            # Default stock locations: Store + Cold Room (suited for an ice-cream/food business)
            store_godown = Godown(
                id=str(uuid.uuid4()),
                code="HO-STORE",
                name="Store",
                branch_id=default_branch.id,
                address=default_branch.address,
                is_default=True,
                is_active=True,
                created_at=datetime.now(timezone.utc)
            )
            cold_room = Godown(
                id=str(uuid.uuid4()),
                code="HO-COLD",
                name="Cold Room",
                branch_id=default_branch.id,
                address=default_branch.address,
                is_default=False,
                is_active=True,
                created_at=datetime.now(timezone.utc)
            )
            session.add_all([store_godown, cold_room])
            await session.commit()

            # Seed Chart of Accounts
            from services.accounting_service import seed_chart_of_accounts
            await seed_chart_of_accounts(session, default_branch.id)

            logger.info("Created default branch, godowns (Store + Cold Room), and chart of accounts")

        # ---- Seed HSN codes ----
        result = await session.execute(select(HSNMaster))
        existing_hsn = result.scalars().first()
        if not existing_hsn:
            hsn_codes = [
                {"hsn_code": "2105", "description": "Ice cream and other edible ice", "gst_rate": 18},
                {"hsn_code": "0401", "description": "Milk and cream, not concentrated", "gst_rate": 0},
                {"hsn_code": "0402", "description": "Milk and cream, concentrated", "gst_rate": 5},
                {"hsn_code": "0405", "description": "Butter and fats from milk", "gst_rate": 12},
                {"hsn_code": "1806", "description": "Chocolate preparations", "gst_rate": 18},
                {"hsn_code": "2106", "description": "Food preparations NES", "gst_rate": 18},
            ]
            for hsn in hsn_codes:
                session.add(HSNMaster(
                    id=str(uuid.uuid4()),
                    **hsn,
                    cess_rate=0,
                    is_active=True,
                    created_at=datetime.now(timezone.utc)
                ))
            await session.commit()
            logger.info("Seeded HSN codes")


@app.on_event("shutdown")
async def shutdown_db_client():
    await engine.dispose()
