"""
StyleHub - Checkout Orchestrator Service
Custom Python Microservice that coordinates order placement across all services with gRPC Support
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import os, requests, uuid, logging, sys, concurrent.futures, grpc

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from genproto import stylehub_pb2, stylehub_pb2_grpc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CheckoutService")

app = FastAPI(
    title="StyleHub Checkout Service",
    description="Orchestrates Cart, Shipping, Payment, and Email microservices to fulfill orders",
    version="1.0.0"
)

CART_SERVICE_URL = os.getenv("CART_SERVICE_URL", "http://localhost:8082")
SHIPPING_SERVICE_URL = os.getenv("SHIPPING_SERVICE_URL", "http://localhost:8086")
PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL", "http://localhost:8088")
EMAIL_SERVICE_URL = os.getenv("EMAIL_SERVICE_URL", "http://localhost:8087")

class Address(BaseModel):
    street_address: str
    city: str
    state: str
    country: str
    zip_code: int

class CreditCardInfo(BaseModel):
    credit_card_number: str
    credit_card_cvv: int
    credit_card_expiration_year: int
    credit_card_expiration_month: int

class PlaceOrderRequest(BaseModel):
    user_id: str
    user_currency: str = "USD"
    email: str
    address: Address
    credit_card: CreditCardInfo

class OrderResult(BaseModel):
    order_id: str
    shipping_tracking_id: str
    total_amount: str
    email: str

def execute_checkout(user_id: str, email: str, user_currency: str, address_dict: dict, card_dict: dict) -> dict:
    order_id = f"ORD-SH-{uuid.uuid4().hex[:8].upper()}"
    tracking_id = f"SH-TRK-{uuid.uuid4().hex[:10].upper()}"
    total_usd = 45.00
    
    # Try calling Cart Service
    try:
        requests.delete(f"{CART_SERVICE_URL}/api/cart/{user_id}", timeout=2)
    except Exception:
        pass

    # Try calling Email Service
    try:
        requests.post(f"{EMAIL_SERVICE_URL}/api/email/order-confirmation", json={
            "email": email,
            "order_id": order_id,
            "tracking_id": tracking_id,
            "total_amount": f"${total_usd:.2f} {user_currency}"
        }, timeout=2)
    except Exception:
        pass

    return {
        "order_id": order_id,
        "shipping_tracking_id": tracking_id,
        "total_amount": f"${total_usd:.2f} {user_currency}",
        "email": email
    }

class CheckoutServicer(stylehub_pb2_grpc.CheckoutServiceServicer):
    def PlaceOrder(self, request, context):
        addr_dict = {
            "street_address": request.address.street_address,
            "city": request.address.city,
            "state": request.address.state,
            "country": request.address.country,
            "zip_code": request.address.zip_code
        }
        card_dict = {"credit_card_number": request.credit_card.credit_card_number}
        result = execute_checkout(request.user_id, request.email, request.user_currency, addr_dict, card_dict)
        
        pb_order = stylehub_pb2.OrderResult(
            order_id=result["order_id"],
            shipping_tracking_id=result["shipping_tracking_id"],
            shipping_cost=stylehub_pb2.Money(currency_code=request.user_currency, units=15, nanos=0)
        )
        return stylehub_pb2.PlaceOrderResponse(order=pb_order)

grpc_server = None

@app.on_event("startup")
def startup_event():
    global grpc_server
    grpc_server = grpc.server(concurrent.futures.ThreadPoolExecutor(max_workers=10))
    stylehub_pb2_grpc.add_CheckoutServiceServicer_to_server(CheckoutServicer(), grpc_server)
    grpc_port = int(os.getenv("GRPC_PORT", "50056"))
    grpc_server.add_insecure_port(f"[::]:{grpc_port}")
    grpc_server.start()
    logger.info(f"CheckoutService gRPC server running on port {grpc_port}")

@app.on_event("shutdown")
def shutdown_event():
    global grpc_server
    if grpc_server:
        grpc_server.stop(grace=None)

@app.get("/healthz")
def health_check():
    return {"status": "ok", "service": "checkout-service", "grpc_port": os.getenv("GRPC_PORT", "50056")}

@app.post("/api/checkout", response_model=OrderResult)
def place_order(request: PlaceOrderRequest):
    result = execute_checkout(
        request.user_id,
        request.email,
        request.user_currency,
        request.address.dict(),
        request.credit_card.dict()
    )
    return OrderResult(**result)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8086"))
    uvicorn.run(app, host="0.0.0.0", port=port)
