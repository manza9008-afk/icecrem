import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from db_models import Base


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/hooren_erp",
)

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Remove sslmode from URL and pass via connect_args
if "?sslmode=" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.split("?sslmode=")[0]

is_local = "localhost" in DATABASE_URL or "127.0.0.1" in DATABASE_URL

engine = create_async_engine(
    DATABASE_URL,
    future=True,
    pool_pre_ping=True,
    connect_args={} if is_local else {"ssl": "require"}
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db():
    async with SessionLocal() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Drop unique constraint on items.code if exists
        try:
            await conn.execute(__import__('sqlalchemy').text(
                "ALTER TABLE items DROP CONSTRAINT IF EXISTS ix_items_code;"
            ))
        except Exception:
            pass
        try:
            await conn.execute(__import__('sqlalchemy').text(
                "DROP INDEX IF EXISTS ix_items_code;"
            ))
        except Exception:
            pass
