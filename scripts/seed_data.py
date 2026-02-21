import asyncio
import sys
sys.path.append('/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient
import os
from datetime import datetime, timezone
import uuid

async def seed_data():
    # Connect to MongoDB
    mongo_url = "mongodb://localhost:27017"
    client = AsyncIOMotorClient(mongo_url)
    db = client["test_database"]
    
    print("Seeding demo data...")
    
    # Sample Categories
    categories = ["Ice Cream Cups", "Ice Cream Cones", "Kulfi", "Bars", "Family Packs"]
    
    # Sample Items
    items = [
        {
            "id": str(uuid.uuid4()),
            "name": "Vanilla Cup 100ml",
            "sku": "IC001",
            "category": "Ice Cream Cups",
            "hsn": "2105",
            "gst_rate": 12,
            "unit": "Piece",
            "cost_price": 15.00,
            "selling_price": 20.00,
            "reorder_level": 50,
            "opening_stock": 100,
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Chocolate Cup 100ml",
            "sku": "IC002",
            "category": "Ice Cream Cups",
            "hsn": "2105",
            "gst_rate": 12,
            "unit": "Piece",
            "cost_price": 16.00,
            "selling_price": 22.00,
            "reorder_level": 50,
            "opening_stock": 120,
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Strawberry Cup 100ml",
            "sku": "IC003",
            "category": "Ice Cream Cups",
            "hsn": "2105",
            "gst_rate": 12,
            "unit": "Piece",
            "cost_price": 17.00,
            "selling_price": 23.00,
            "reorder_level": 40,
            "opening_stock": 80,
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Mango Kulfi",
            "sku": "KF001",
            "category": "Kulfi",
            "hsn": "2105",
            "gst_rate": 12,
            "unit": "Piece",
            "cost_price": 12.00,
            "selling_price": 18.00,
            "reorder_level": 60,
            "opening_stock": 150,
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Family Pack Vanilla 1L",
            "sku": "FP001",
            "category": "Family Packs",
            "hsn": "2105",
            "gst_rate": 12,
            "unit": "Box",
            "cost_price": 120.00,
            "selling_price": 150.00,
            "reorder_level": 20,
            "opening_stock": 30,
            "created_at": datetime.now(timezone.utc).isoformat()
        },
    ]
    
    # Insert items
    await db.items.insert_many(items)
    print(f"Inserted {len(items)} items")
    
    # Initialize stock for items
    for item in items:
        await db.stock_transactions.insert_one({
            "id": str(uuid.uuid4()),
            "item_id": item["id"],
            "transaction_type": "opening",
            "quantity": item["opening_stock"],
            "date": datetime.now(timezone.utc).isoformat(),
            "reference": "Opening Stock"
        })
    
    # Sample Customers
    customers = [
        {
            "id": str(uuid.uuid4()),
            "name": "Patel General Store",
            "address": "Main Market, Patan, Gujarat",
            "gstin": "24XXXXX1234X1Z5",
            "pan": None,
            "phone": "9876543210",
            "email": "patel.store@example.com",
            "credit_limit": 50000,
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Shah Retail Mart",
            "address": "Station Road, Patan, Gujarat",
            "gstin": "24YYYYY5678Y2Z6",
            "pan": None,
            "phone": "9876543211",
            "email": None,
            "credit_limit": 30000,
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Krishna Ice Cream Parlour",
            "address": "College Road, Patan, Gujarat",
            "gstin": None,
            "pan": None,
            "phone": "9876543212",
            "email": None,
            "credit_limit": 0,
            "created_at": datetime.now(timezone.utc).isoformat()
        },
    ]
    
    await db.customers.insert_many(customers)
    print(f"Inserted {len(customers)} customers")
    
    # Create ledgers for customers
    for customer in customers:
        await db.ledgers.insert_one({
            "id": str(uuid.uuid4()),
            "name": customer["name"],
            "group": "Sundry Debtors",
            "opening_balance": 0,
            "balance": 0,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    
    # Sample Suppliers
    suppliers = [
        {
            "id": str(uuid.uuid4()),
            "name": "Gujarat Dairy Products Ltd",
            "address": "Mehsana, Gujarat",
            "gstin": "24AAAAA1111A1Z1",
            "pan": "AAAAA1111A",
            "phone": "9123456789",
            "email": "sales@gujaratdairy.com",
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Amul Distributors",
            "address": "Anand, Gujarat",
            "gstin": "24BBBBB2222B2Z2",
            "pan": "BBBBB2222B",
            "phone": "9123456790",
            "email": "info@amuldist.com",
            "created_at": datetime.now(timezone.utc).isoformat()
        },
    ]
    
    await db.suppliers.insert_many(suppliers)
    print(f"Inserted {len(suppliers)} suppliers")
    
    # Create ledgers for suppliers
    for supplier in suppliers:
        await db.ledgers.insert_one({
            "id": str(uuid.uuid4()),
            "name": supplier["name"],
            "group": "Sundry Creditors",
            "opening_balance": 0,
            "balance": 0,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    
    print("Demo data seeded successfully!")
    client.close()

if __name__ == "__main__":
    asyncio.run(seed_data())
