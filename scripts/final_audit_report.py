import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "backend"))

from sqlalchemy import select, func

from database import SessionLocal, init_db
from db_models import Branch, Customer, Item, Ledger, Supplier, User


async def main():
    await init_db()
    report = {"database": "postgresql", "tables": {}}
    async with SessionLocal() as session:
        for model in [User, Branch, Ledger, Item, Customer, Supplier]:
            result = await session.execute(select(func.count(model.id)))
            report["tables"][model.__tablename__] = result.scalar() or 0

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
