-- HOOREN FOOD PRODUCTS ERP
-- PostgreSQL bootstrap schema
--
-- The FastAPI backend creates the complete schema from SQLAlchemy models on
-- startup via backend/database.py:init_db(). This file is kept as a simple
-- database bootstrap for manual setup.

CREATE DATABASE hooren_erp;

-- After creating the database, run the backend once with:
-- DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/hooren_erp
-- uvicorn server:app --reload
