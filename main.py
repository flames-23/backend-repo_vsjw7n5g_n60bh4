import os
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Product, Order, ShelfCell, DispenseLog, User, OrderItem

app = FastAPI(title="AeroShelf API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "AeroShelf Backend Running"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response

# ----- Auth (Minimal placeholder — extend with proper auth in real app) -----
class AuthPayload(BaseModel):
    email: str
    name: Optional[str] = None

@app.post("/auth/upsert")
def upsert_user(payload: AuthPayload):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    existing = db["user"].find_one({"email": payload.email})
    if existing:
        db["user"].update_one({"_id": existing["_id"]}, {"$set": {"name": payload.name or existing.get("name", ""), "is_active": True}})
        return {"status": "updated"}
    uid = create_document("user", User(email=payload.email, name=payload.name or "User", role="customer"))
    return {"status": "created", "id": uid}

# ----- Products -----
@app.post("/products")
def create_product(product: Product):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    pid = create_document("product", product)
    return {"id": pid}

@app.get("/products")
def list_products() -> List[dict]:
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    docs = get_documents("product")
    for d in docs:
        d["id"] = str(d.pop("_id"))
    return docs

# ----- Shelf Map (A1..A20) -----
@app.get("/shelves")
def get_shelves() -> List[dict]:
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    docs = get_documents("shelfcell")
    if not docs:
        # seed 20 cells
        for i in range(1, 21):
            create_document("shelfcell", ShelfCell(cell_code=f"A{i}", stock=0))
        docs = get_documents("shelfcell")
    for d in docs:
        d["id"] = str(d.pop("_id"))
    return docs

@app.post("/shelves/{cell_code}/motor")
def toggle_motor(cell_code: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    cell = db["shelfcell"].find_one({"cell_code": cell_code})
    if not cell:
        raise HTTPException(404, "Cell not found")
    new_state = not cell.get("motor_active", False)
    db["shelfcell"].update_one({"_id": cell["_id"]}, {"$set": {"motor_active": new_state}})
    return {"cell_code": cell_code, "motor_active": new_state}

# ----- Orders & Dispensing -----
class OrderCreate(BaseModel):
    user_email: str
    items: List[OrderItem]

@app.post("/orders")
def create_order(payload: OrderCreate):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    total = sum(i.quantity for i in payload.items)
    order = Order(user_email=payload.user_email, items=payload.items, total_items=total, status="processing", progress=0)
    oid = create_document("order", order)
    return {"id": oid, "status": order.status, "progress": order.progress}

@app.get("/orders/{order_id}")
def get_order(order_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    doc = db["order"].find_one({"_id": ObjectId(order_id)})
    if not doc:
        raise HTTPException(404, "Order not found")
    doc["id"] = str(doc.pop("_id"))
    return doc

@app.post("/orders/{order_id}/progress")
def set_order_progress(order_id: str, progress: int):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    progress = max(0, min(100, progress))
    status = "ready" if progress >= 100 else "processing"
    db["order"].update_one({"_id": ObjectId(order_id)}, {"$set": {"progress": progress, "status": status}})
    return {"id": order_id, "progress": progress, "status": status}

# ----- Schema export (for tooling) -----
@app.get("/schema")
def get_schema():
    return {
        "models": [
            "user",
            "product",
            "order",
            "shelfcell",
            "dispenselog",
        ]
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
