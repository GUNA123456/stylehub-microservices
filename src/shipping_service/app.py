"""
StyleHub - Shipping Service
Custom Python Microservice calculating shipping rates & tracking with gRPC Support
"""

from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import os, uuid, sys, concurrent.futures, grpc

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from genproto import stylehub_pb2, stylehub_pb2_grpc

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

def calculate_shipping_cost(items) -> tuple:
    total_count = sum(item.quantity for item in items)
    base_cost = 8.99 + (total_count * 1.50)
    units = int(base_cost)
    nanos = int((base_cost - units) * 1e9)
    return units, nanos

class ShippingServicer(stylehub_pb2_grpc.ShippingServiceServicer):
    def GetQuote(self, request, context):
        units, nanos = calculate_shipping_cost(request.items)
        cost = stylehub_pb2.Money(currency_code="USD", units=units, nanos=nanos)
        return stylehub_pb2.GetQuoteResponse(cost_usd=cost)

    def ShipOrder(self, request, context):
        tracking_code = f"SH-TRK-{uuid.uuid4().hex[:10].upper()}"
        return stylehub_pb2.ShipOrderResponse(tracking_id=tracking_code)

grpc_server = None

@app.on_event("startup")
def startup_event():
    global grpc_server
    grpc_server = grpc.server(concurrent.futures.ThreadPoolExecutor(max_workers=10))
    stylehub_pb2_grpc.add_ShippingServiceServicer_to_server(ShippingServicer(), grpc_server)
    grpc_port = int(os.getenv("GRPC_PORT", "50055"))
    grpc_server.add_insecure_port(f"[::]:{grpc_port}")
    grpc_server.start()
    print(f"ShippingService gRPC server running on port {grpc_port}")

@app.on_event("shutdown")
def shutdown_event():
    global grpc_server
    if grpc_server:
        grpc_server.stop(grace=None)

@app.get("/healthz")
def health_check():
    return {"status": "ok", "service": "shipping-service", "grpc_port": os.getenv("GRPC_PORT", "50055")}

@app.post("/api/shipping/quote", response_model=QuoteResponse)
def get_quote(request: QuoteRequest):
    units, nanos = calculate_shipping_cost(request.items)
    return QuoteResponse(cost_usd={"currency_code": "USD", "units": units, "nanos": nanos})

@app.post("/api/shipping/ship", response_model=ShipOrderResponse)
def ship_order(request: ShipOrderRequest):
    tracking_code = f"SH-TRK-{uuid.uuid4().hex[:10].upper()}"
    return ShipOrderResponse(tracking_id=tracking_code)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8085"))
    uvicorn.run(app, host="0.0.0.0", port=port)
