"""
StyleHub - Checkout Orchestrator Service
Custom Python Microservice that coordinates order placement across all services
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import os, requests, uuid, logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CheckoutService")

app = FastAPI(
    title="StyleHub Checkout Service",
    description="Orchestrates Cart, Shipping, Payment, and Email microservices to fulfill orders",
    version="1.0.0"
)

# Service endpoints (configurable via ENV for Kubernetes / Docker Compose)
CART_SERVICE_URL = os.getenv("CART_SERVICE_URL", "http://localhost:8082")
SHIPPING_SERVICE_URL = os.getenv("SHIPPING_SERVICE_URL", "http://localhost:8086")
PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL", "http://localhost:8088")
EMAIL_SERVICE_URL = os.getenv("EMAIL_SERVICE_URL", "http://localhost:8087")
PRODUCT_SERVICE_URL = os.getenv("PRODUCT_CATALOG_SERVICE_URL", "http://localhost:8081")

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

@app.get("/healthz")
def health_check():
    return {"status": "ok", "service": "checkout-service"}

@app.post("/api/checkout", response_model=OrderResult)
def place_order(request: PlaceOrderRequest):
    """Executes the full checkout workflow across multiple microservices."""
    user_id = request.user_id
    logger.info(f"🛒 [CHECKOUT STARTED] User: {user_id}")

    # 1. Fetch User Cart
    try:
        cart_resp = requests.get(f"{CART_SERVICE_URL}/api/cart/{user_id}", timeout=5)
        cart_data = cart_resp.json()
        items = cart_data.get("items", [])
        if not items:
            raise HTTPException(status_code=400, detail="Cart is empty")
    except requests.RequestException as e:
        logger.error(f"Failed to reach Cart Service ({CART_SERVICE_URL}): {e}")
        raise HTTPException(status_code=500, detail="Cart Service unavailable")

    # 2. Calculate Shipping Quote & Dispatch Shipping
    try:
        ship_resp = requests.post(f"{SHIPPING_SERVICE_URL}/api/shipping/ship", json={
            "address": request.address.dict(),
            "items": items
        }, timeout=5)
        tracking_id = ship_resp.json().get("tracking_id", "SH-TRK-PENDING")
    except requests.RequestException:
        tracking_id = f"SH-TRK-{uuid.uuid4().hex[:8].upper()}"

    # 3. Calculate Total Price
    total_usd = 15.00  # Default base + items calculation
    for item in items:
        total_usd += (25.00 * item.get("quantity", 1))

    # 4. Charge Payment
    try:
        pay_resp = requests.post(f"{PAYMENT_SERVICE_URL}/api/payment/charge", json={
            "amount": {"currency_code": request.user_currency, "units": int(total_usd), "nanos": 0},
            "credit_card": request.credit_card.dict()
        }, timeout=5)
        if pay_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Payment declined")
    except requests.RequestException as e:
        logger.error(f"Payment error: {e}")
        raise HTTPException(status_code=500, detail="Payment Service unavailable")

    order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
    total_str = f"{total_usd:.2f} {request.user_currency}"

    # 5. Send Email Notification
    try:
        requests.post(f"{EMAIL_SERVICE_URL}/api/email/order-confirmation", json={
            "email": request.email,
            "order_id": order_id,
            "tracking_id": tracking_id,
            "total_amount": total_str
        }, timeout=3)
    except Exception as e:
        logger.warning(f"Non-fatal email dispatch warning: {e}")

    # 6. Empty User Cart
    try:
        requests.delete(f"{CART_SERVICE_URL}/api/cart/{user_id}", timeout=3)
    except Exception as e:
        logger.warning(f"Non-fatal cart clear warning: {e}")

    logger.info(f"✅ [ORDER COMPLETED] Order ID: {order_id}")
    return OrderResult(
        order_id=order_id,
        shipping_tracking_id=tracking_id,
        total_amount=total_str,
        email=request.email
    )

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8089"))
    uvicorn.run(app, host="0.0.0.0", port=port)
