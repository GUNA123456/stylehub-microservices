"""
StyleHub - Shipping Service
Custom Python Microservice calculating shipping rates & tracking
"""

from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import os, uuid

app = FastAPI(
    title="StyleHub Shipping Service",
    description="Estimates shipping rates and generates tracking IDs for StyleHub orders",
    version="1.0.0"
)

class Address(BaseModel):
    street_address: str
    city: str
    state: str
    country: str
    zip_code: int

class CartItem(BaseModel):
    product_id: str
    quantity: int

class QuoteRequest(BaseModel):
    address: Address
    items: List[CartItem]

class QuoteResponse(BaseModel):
    cost_usd: dict

class ShipOrderRequest(BaseModel):
    address: Address
    items: List[CartItem]

class ShipOrderResponse(BaseModel):
    tracking_id: str

@app.get("/healthz")
def health_check():
    return {"status": "ok", "service": "shipping-service"}

@app.post("/api/shipping/quote", response_model=QuoteResponse)
def get_quote(request: QuoteRequest):
    """Calculates flat-rate or item-count based shipping cost."""
    total_count = sum(item.quantity for item in request.items)
    # Base fee $8.99 + $1.50 per item
    base_cost = 8.99 + (total_count * 1.50)
    units = int(base_cost)
    nanos = int((base_cost - units) * 1e9)
    return QuoteResponse(cost_usd={"currency_code": "USD", "units": units, "nanos": nanos})

@app.post("/api/shipping/ship", response_model=ShipOrderResponse)
def ship_order(request: ShipOrderRequest):
    """Generates a unique carrier tracking ID for a dispatched order."""
    tracking_code = f"SH-TRK-{uuid.uuid4().hex[:10].upper()}"
    return ShipOrderResponse(tracking_id=tracking_code)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8086"))
    uvicorn.run(app, host="0.0.0.0", port=port)
