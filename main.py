import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

from database import db, create_document, get_documents
from schemas import Service, QuoteRequest

app = FastAPI(title="Print Studio API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Print Studio Backend Ready"}

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
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = getattr(db, 'name', None) or "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:80]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"
    return response

# Seed some default services if collection empty
@app.post("/seed/services")
def seed_services():
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    existing = db["service"].count_documents({})
    if existing > 0:
        return {"seeded": False, "message": "Services already exist"}

    defaults: List[Service] = [
        Service(
            key="tshirt",
            name="T‑Shirt Printing",
            description="DTG and screen printing for tees",
            base_price=6.0,
            categories=["apparel", "tshirt"],
            color_price_per_color=0.35,
            print_area_multiplier=1.0,
            minimum_quantity=1,
        ),
        Service(
            key="tote_bag",
            name="Tote Bag Printing",
            description="Durable cotton tote prints",
            base_price=4.0,
            categories=["bags", "tote"],
            color_price_per_color=0.25,
            print_area_multiplier=1.1,
            minimum_quantity=1,
        ),
        Service(
            key="hoodie",
            name="Hoodie Printing",
            description="Premium hoodies with vivid prints",
            base_price=12.0,
            categories=["apparel", "hoodie"],
            color_price_per_color=0.4,
            print_area_multiplier=1.2,
            minimum_quantity=1,
        ),
    ]

    for s in defaults:
        create_document("service", s)

    return {"seeded": True, "count": len(defaults)}

# Pricing logic
class PriceRequest(BaseModel):
    service_key: str
    quantity: int
    colors: int = 1
    print_area: str = "medium"  # small, medium, large

class PriceResponse(BaseModel):
    unit_price: float
    total_price: float
    breakdown: dict

@app.get("/services", response_model=List[Service])
def list_services():
    docs = get_documents("service")
    return [Service(**{k: v for k, v in d.items() if k != "_id"}) for d in docs]

@app.post("/price", response_model=PriceResponse)
def calculate_price(req: PriceRequest):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    svc_doc = db["service"].find_one({"key": req.service_key})
    if not svc_doc:
        raise HTTPException(status_code=404, detail="Service not found")
    service = Service(**{k: v for k, v in svc_doc.items() if k != "_id"})

    area_multiplier_map = {"small": 0.9, "medium": 1.0, "large": service.print_area_multiplier}
    area_mult = area_multiplier_map.get(req.print_area, 1.0)

    unit = service.base_price
    color_add = max(0, req.colors - 1) * service.color_price_per_color
    unit_price = round((unit + color_add) * area_mult, 2)

    # volume discount for low price positioning
    if req.quantity >= 100:
        unit_price *= 0.75
    elif req.quantity >= 50:
        unit_price *= 0.82
    elif req.quantity >= 20:
        unit_price *= 0.9
    unit_price = round(unit_price, 2)

    if req.quantity < service.minimum_quantity:
        raise HTTPException(status_code=400, detail=f"Minimum quantity is {service.minimum_quantity}")

    total_price = round(unit_price * req.quantity, 2)

    return PriceResponse(
        unit_price=unit_price,
        total_price=total_price,
        breakdown={
            "base": service.base_price,
            "colors": req.colors,
            "color_add_per_unit": service.color_price_per_color,
            "area_multiplier": area_mult,
            "volume_discounts": True,
        },
    )

@app.post("/quotes")
def create_quote(q: QuoteRequest):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    # Calculate estimated price and store with quote
    price = calculate_price(PriceRequest(
        service_key=q.service_key,
        quantity=q.quantity,
        colors=q.colors,
        print_area=q.print_area,
    ))

    q.estimated_total = price.total_price
    doc_id = create_document("quoterequest", q)
    return {"id": doc_id, "estimated_total": price.total_price}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
