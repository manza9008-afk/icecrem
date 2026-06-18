import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "backend"))

from sqlalchemy import select, func

from database import SessionLocal, init_db
from db_models import Branch, Customer, Item, Ledger, Supplier, User


async def main():
    await init_db()
    checks = {}
    async with SessionLocal() as session:
        for model in [User, Branch, Ledger, Item, Customer, Supplier]:
            result = await session.execute(select(func.count(model.id)))
            checks[model.__tablename__] = result.scalar() or 0

    print("PostgreSQL system audit")
    for table, count in checks.items():
        print(f"{table}: {count}")


if __name__ == "__main__":
    asyncio.run(main())
