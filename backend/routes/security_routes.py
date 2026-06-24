"""
HOOREN ERP - Security & Audit Routes
Role-Based Access Control, Audit Logs, User Management
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime, timezone
import uuid
import hashlib
import json

router = APIRouter(prefix="/api/security", tags=["security"])

from server import db
from utils import get_current_user

# ==================== ROLES ====================

SYSTEM_ROLES = [
    {
        "code": "ADMIN",
        "name": "Administrator",
        "description": "Full system access with all permissions",
        "permissions": ["*"],
        "is_system": True
    },
    {
        "code": "MANAGER",
        "name": "Branch Manager",
        "description": "Full access to branch operations",
        "permissions": [
            "masters.*", "accounting.*", "sales.*", "purchase.*",
            "inventory.*", "reports.*", "gst.*"
        ],
        "is_system": True
    },
    {
        "code": "ACCOUNTANT",
        "name": "Accountant",
        "description": "Access to accounting and reports",
        "permissions": [
            "accounting.*", "reports.*", "gst.*",
            "masters.ledgers.read", "masters.ledgers.create",
            "sales.invoices.read", "purchase.invoices.read"
        ],
        "is_system": True
    },
    {
        "code": "SALES_EXEC",
        "name": "Sales Executive",
        "description": "Access to sales module only",
        "permissions": [
            "sales.*", "masters.customers.*", "masters.items.read",
            "inventory.stock.read", "reports.sales.*"
        ],
        "is_system": True
    },
    {
        "code": "PURCHASE_EXEC",
        "name": "Purchase Executive",
        "description": "Access to purchase module only",
        "permissions": [
            "purchase.*", "masters.suppliers.*", "masters.items.read",
            "inventory.stock.read", "reports.purchase.*"
        ],
        "is_system": True
    },
    {
        "code": "INVENTORY_CLERK",
        "name": "Inventory Clerk",
        "description": "Access to inventory management",
        "permissions": [
            "inventory.*", "masters.items.*", "masters.godowns.read",
            "reports.stock.*"
        ],
        "is_system": True
    },
    {
        "code": "VIEWER",
        "name": "View Only",
        "description": "Read-only access to all modules",
        "permissions": [
            "*.read", "reports.*"
        ],
        "is_system": True
    }
]

PERMISSION_MODULES = [
    "masters.branches", "masters.godowns", "masters.ledgers", "masters.items",
    "masters.customers", "masters.suppliers", "masters.account_groups",
    "accounting.vouchers", "accounting.journal", "accounting.payment",
    "accounting.receipt", "accounting.contra",
    "sales.quotations", "sales.orders", "sales.invoices", "sales.returns",
    "purchase.orders", "purchase.invoices", "purchase.returns",
    "inventory.stock", "inventory.transfers", "inventory.adjustments",
    "reports.trial_balance", "reports.profit_loss", "reports.balance_sheet",
    "reports.day_book", "reports.ledger_statement", "reports.stock",
    "gst.gstr1", "gst.gstr3b", "gst.hsn", "gst.liability",
    "security.users", "security.roles", "security.audit"
]


@router.get("/roles")
async def get_roles(current_user: dict = Depends(get_current_user)):
    """Get all roles"""
    roles = await db.roles.find({}, {"_id": 0}).to_list(100)
    if not roles:
        # Seed system roles
        for role in SYSTEM_ROLES:
            role_doc = {
                "id": str(uuid.uuid4()),
                **role,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.roles.insert_one(role_doc)
        roles = await db.roles.find({}, {"_id": 0}).to_list(100)
    return roles


@router.get("/roles/{role_id}")
async def get_role(role_id: str, current_user: dict = Depends(get_current_user)):
    """Get role details"""
    role = await db.roles.find_one({"id": role_id}, {"_id": 0})
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return role


@router.post("/roles")
async def create_role(role_data: dict, current_user: dict = Depends(get_current_user)):
    """Create a custom role"""
    # Check code uniqueness
    existing = await db.roles.find_one({"code": role_data["code"]})
    if existing:
        raise HTTPException(status_code=400, detail="Role code already exists")
    
    role_doc = {
        "id": str(uuid.uuid4()),
        **role_data,
        "is_system": False,
        "created_by": current_user["username"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.roles.insert_one(role_doc)
    role_doc.pop("_id", None)
    
    # Audit log
    await log_audit(db, "ROLE_CREATED", "role", role_doc["id"], None, role_doc, current_user)
    
    return role_doc


@router.put("/roles/{role_id}")
async def update_role(
    role_id: str,
    role_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Update role"""
    existing = await db.roles.find_one({"id": role_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Role not found")
    
    if existing.get("is_system"):
        raise HTTPException(status_code=400, detail="Cannot modify system role")
    
    old_data = {k: v for k, v in existing.items() if k != "_id"}
    
    role_data["modified_at"] = datetime.now(timezone.utc).isoformat()
    role_data["modified_by"] = current_user["username"]
    
    await db.roles.update_one({"id": role_id}, {"$set": role_data})
    
    # Audit log
    await log_audit(db, "ROLE_UPDATED", "role", role_id, old_data, role_data, current_user)
    
    return {"message": "Role updated"}


@router.delete("/roles/{role_id}")
async def delete_role(role_id: str, current_user: dict = Depends(get_current_user)):
    """Delete role"""
    existing = await db.roles.find_one({"id": role_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Role not found")
    
    if existing.get("is_system"):
        raise HTTPException(status_code=400, detail="Cannot delete system role")
    
    # Check if users have this role
    users_with_role = await db.users.count_documents({"role_id": role_id})
    if users_with_role > 0:
        raise HTTPException(status_code=400, detail=f"Cannot delete. {users_with_role} users have this role")
    
    await db.roles.delete_one({"id": role_id})
    
    # Audit log
    await log_audit(db, "ROLE_DELETED", "role", role_id, existing, None, current_user)
    
    return {"message": "Role deleted"}


@router.get("/permissions")
async def get_permissions(current_user: dict = Depends(get_current_user)):
    """Get all available permissions"""
    permissions = []
    for module in PERMISSION_MODULES:
        permissions.append({
            "module": module,
            "actions": ["create", "read", "update", "delete"]
        })
    return permissions


# ==================== USER MANAGEMENT ====================

@router.get("/users")
async def get_users(
    branch_id: Optional[str] = None,
    role_id: Optional[str] = None,
    is_active: bool = True,
    current_user: dict = Depends(get_current_user)
):
    """Get all users"""
    query = {}
    if branch_id:
        query["branch_id"] = branch_id
    if role_id:
        query["role_id"] = role_id
    if is_active is not None:
        query["is_active"] = is_active
    
    users = await db.users.find(query, {"_id": 0, "password": 0}).to_list(1000)
    
    # Enrich with role info
    roles = await db.roles.find({}, {"_id": 0}).to_list(100)
    roles_dict = {r["id"]: r for r in roles}
    
    for user in users:
        role = roles_dict.get(user.get("role_id"), {})
        user["role_name"] = role.get("name", "Unknown")
        user["role_code"] = role.get("code", "")
    
    return users


@router.get("/users/{user_id}")
async def get_user(user_id: str, current_user: dict = Depends(get_current_user)):
    """Get user details"""
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    role = await db.roles.find_one({"id": user.get("role_id")}, {"_id": 0})
    user["role"] = role
    
    return user


@router.post("/users")
async def create_user(user_data: dict, current_user: dict = Depends(get_current_user)):
    """Create a new user"""
    # Check username uniqueness
    existing = await db.users.find_one({"username": user_data["username"]})
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # Validate role
    if user_data.get("role_id"):
        role = await db.roles.find_one({"id": user_data["role_id"]})
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")
    
    # Hash password
    import bcrypt
    password = user_data.pop("password", "Password@123")
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    
    user_doc = {
        "id": str(uuid.uuid4()),
        **user_data,
        "password": hashed,
        "is_active": True,
        "must_change_password": True,
        "failed_login_attempts": 0,
        "created_by": current_user["username"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(user_doc)
    user_doc.pop("_id", None)
    user_doc.pop("password", None)
    
    # Audit log
    await log_audit(db, "USER_CREATED", "user", user_doc["id"], None, user_doc, current_user)
    
    return user_doc


@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    user_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Update user"""
    existing = await db.users.find_one({"id": user_id})
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")
    
    old_data = {k: v for k, v in existing.items() if k not in ["_id", "password"]}
    
    # Handle password change
    if "password" in user_data:
        import bcrypt
        password = user_data.pop("password")
        user_data["password"] = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        user_data["must_change_password"] = False
        user_data["password_changed_at"] = datetime.now(timezone.utc).isoformat()
    
    user_data["modified_at"] = datetime.now(timezone.utc).isoformat()
    user_data["modified_by"] = current_user["username"]
    
    await db.users.update_one({"id": user_id}, {"$set": user_data})
    
    # Audit log
    audit_data = {k: v for k, v in user_data.items() if k != "password"}
    await log_audit(db, "USER_UPDATED", "user", user_id, old_data, audit_data, current_user)
    
    return {"message": "User updated"}


@router.delete("/users/{user_id}")
async def deactivate_user(user_id: str, current_user: dict = Depends(get_current_user)):
    """Deactivate user (soft delete)"""
    existing = await db.users.find_one({"id": user_id})
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")
    
    if existing["id"] == current_user.get("id"):
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")
    
    await db.users.update_one(
        {"id": user_id},
        {"$set": {
            "is_active": False,
            "deactivated_at": datetime.now(timezone.utc).isoformat(),
            "deactivated_by": current_user["username"]
        }}
    )
    
    # Audit log
    await log_audit(db, "USER_DEACTIVATED", "user", user_id, None, None, current_user)
    
    return {"message": "User deactivated"}


# ==================== AUDIT LOGS ====================

async def log_audit(
    db,
    action: str,
    entity_type: str,
    entity_id: str,
    old_data: dict = None,
    new_data: dict = None,
    current_user: dict = None,
    metadata: dict = None
):
    """Create audit log entry"""
    
    # Create hash of data for integrity
    data_string = json.dumps({"old": old_data, "new": new_data}, sort_keys=True, default=str)
    data_hash = hashlib.sha256(data_string.encode()).hexdigest()
    
    audit_doc = {
        "id": str(uuid.uuid4()),
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "old_data": old_data,
        "new_data": new_data,
        "data_hash": data_hash,
        "user_id": current_user.get("id") if current_user else None,
        "username": current_user.get("username") if current_user else "SYSTEM",
        "branch_id": current_user.get("branch_id") if current_user else None,
        "ip_address": metadata.get("ip_address") if metadata else None,
        "user_agent": metadata.get("user_agent") if metadata else None,
        "metadata": metadata,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.audit_logs.insert_one(audit_doc)
    return audit_doc


@router.get("/audit-logs")
async def get_audit_logs(
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    action: Optional[str] = None,
    user_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 500,
    current_user: dict = Depends(get_current_user)
):
    """Get audit logs with filters"""
    query = {}
    
    if entity_type:
        query["entity_type"] = entity_type
    if entity_id:
        query["entity_id"] = entity_id
    if action:
        query["action"] = action
    if user_id:
        query["user_id"] = user_id
    
    if start_date or end_date:
        date_query = {}
        if start_date:
            date_query["$gte"] = start_date
        if end_date:
            date_query["$lte"] = end_date
        if date_query:
            query["created_at"] = date_query
    
    logs = await db.audit_logs.find(
        query, {"_id": 0}
    ).sort("created_at", -1).to_list(limit)
    
    return logs


@router.get("/audit-logs/{log_id}")
async def get_audit_log(log_id: str, current_user: dict = Depends(get_current_user)):
    """Get audit log details"""
    log = await db.audit_logs.find_one({"id": log_id}, {"_id": 0})
    if not log:
        raise HTTPException(status_code=404, detail="Audit log not found")
    return log


@router.get("/audit-logs/entity/{entity_type}/{entity_id}")
async def get_entity_audit_trail(
    entity_type: str,
    entity_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get complete audit trail for an entity"""
    logs = await db.audit_logs.find(
        {"entity_type": entity_type, "entity_id": entity_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(1000)
    
    return {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "total_changes": len(logs),
        "audit_trail": logs
    }


# ==================== USER ACTIVITY ====================

@router.get("/user-activity")
async def get_user_activity(
    user_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
    current_user: dict = Depends(get_current_user)
):
    """Get user activity logs"""
    query = {}
    
    if user_id:
        query["user_id"] = user_id
    
    if start_date or end_date:
        date_query = {}
        if start_date:
            date_query["$gte"] = start_date
        if end_date:
            date_query["$lte"] = end_date
        if date_query:
            query["created_at"] = date_query
    
    activities = await db.user_activities.find(
        query, {"_id": 0}
    ).sort("created_at", -1).to_list(limit)
    
    return activities


async def log_user_activity(
    db,
    user_id: str,
    username: str,
    activity_type: str,
    description: str,
    metadata: dict = None
):
    """Log user activity"""
    activity_doc = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "username": username,
        "activity_type": activity_type,
        "description": description,
        "metadata": metadata,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.user_activities.insert_one(activity_doc)
    return activity_doc


# ==================== SESSION MANAGEMENT ====================

@router.get("/sessions")
async def get_active_sessions(current_user: dict = Depends(get_current_user)):
    """Get all active sessions for current user"""
    sessions = await db.user_sessions.find(
        {"user_id": current_user["id"], "is_active": True},
        {"_id": 0}
    ).to_list(100)
    
    return sessions


@router.delete("/sessions/{session_id}")
async def terminate_session(session_id: str, current_user: dict = Depends(get_current_user)):
    """Terminate a session"""
    session = await db.user_sessions.find_one({"id": session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Only allow terminating own sessions or admin
    if session["user_id"] != current_user["id"]:
        # Check if admin
        user_role = await db.roles.find_one({"id": current_user.get("role_id")})
        if not user_role or user_role.get("code") != "ADMIN":
            raise HTTPException(status_code=403, detail="Not authorized")
    
    await db.user_sessions.update_one(
        {"id": session_id},
        {"$set": {
            "is_active": False,
            "terminated_at": datetime.now(timezone.utc).isoformat(),
            "terminated_by": current_user["username"]
        }}
    )
    
    return {"message": "Session terminated"}


# ==================== PERMISSION CHECK HELPER ====================

async def check_permission(db, user_id: str, permission: str) -> bool:
    """Check if user has specific permission"""
    user = await db.users.find_one({"id": user_id})
    if not user:
        return False
    
    role = await db.roles.find_one({"id": user.get("role_id")})
    if not role:
        return False
    
    permissions = role.get("permissions", [])
    
    # Check for wildcard
    if "*" in permissions:
        return True
    
    # Check exact match
    if permission in permissions:
        return True
    
    # Check module wildcard
    module = permission.rsplit(".", 1)[0]
    if f"{module}.*" in permissions:
        return True
    
    # Check action wildcard
    action = permission.rsplit(".", 1)[-1]
    if f"*.{action}" in permissions:
        return True
    
    return False
