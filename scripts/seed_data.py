import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "backend"))

from database import SessionLocal, init_db
from db_models import Customer, Item, Ledger, Supplier


async def seed_data():
    await init_db()
    async with SessionLocal() as session:
        now = datetime.now(timezone.utc)

        items = [
            Item(
                id=str(uuid.uuid4()),
                code="IC001",
                name="Vanilla Cup 100ml",
                category="Ice Cream Cups",
                hsn_code="2105",
                unit="Piece",
                gst_rate=12,
                cost_price=15,
                selling_price=20,
                reorder_level=50,
                opening_stock=100,
                is_active=True,
                created_at=now,
            ),
            Item(
                id=str(uuid.uuid4()),
                code="IC002",
                name="Chocolate Cup 100ml",
                category="Ice Cream Cups",
                hsn_code="2105",
                unit="Piece",
                gst_rate=12,
                cost_price=16,
                selling_price=22,
                reorder_level=50,
                opening_stock=120,
                is_active=True,
                created_at=now,
            ),
        ]

        customers = [
            Customer(
                id=str(uuid.uuid4()),
                name="Patel General Store",
                address="Main Market, Patan, Gujarat",
                gstin="24XXXXX1234X1Z5",
                phone="9876543210",
                email="patel.store@example.com",
                credit_limit=50000,
                is_active=True,
                created_at=now,
            ),
            Customer(
                id=str(uuid.uuid4()),
                name="Shah Retail Mart",
                address="Station Road, Patan, Gujarat",
                gstin="24YYYYY5678Y2Z6",
                phone="9876543211",
                credit_limit=30000,
                is_active=True,
                created_at=now,
            ),
        ]

        suppliers = [
            Supplier(
                id=str(uuid.uuid4()),
                name="Gujarat Dairy Products Ltd",
                address="Mehsana, Gujarat",
                gstin="24AAAAA1111A1Z1",
                pan="AAAAA1111A",
                phone="9123456789",
                email="sales@gujaratdairy.com",
                is_active=True,
                created_at=now,
            )
        ]

        ledgers = [
            Ledger(
                id=str(uuid.uuid4()),
                name=customer.name,
                code=customer.name.upper().replace(" ", "_"),
                account_group_id="",
                branch_id=None,
                opening_balance=0,
                balance_type="debit",
                current_balance=0,
                is_party=True,
                is_active=True,
                created_at=now,
            )
            for customer in customers
        ]

        session.add_all(items + customers + suppliers + ledgers)
        await session.commit()

    print("PostgreSQL demo data seeded successfully.")


if __name__ == "__main__":
    asyncio.run(seed_data())
