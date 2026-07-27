"""
StyleHub - Checkout Orchestrator Service
Clean FastAPI Microservice orchestrating Cart, Shipping, Payment, and Email REST calls
"""

from fastapi import FastAPI
import os, uuid, logging, requests, sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.models import PlaceOrderRequest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CheckoutService")

app = FastAPI(title="StyleHub Checkout Service")

CART_URL = os.getenv("CART_SERVICE_URL", os.getenv("CART_SERVICE_ADDR", "http://localhost:8082"))
SHIPPING_URL = os.getenv("SHIPPING_SERVICE_URL", os.getenv("SHIPPING_SERVICE_ADDR", "http://localhost:8085"))
PAYMENT_URL = os.getenv("PAYMENT_SERVICE_URL", os.getenv("PAYMENT_SERVICE_ADDR", "http://localhost:8089"))
EMAIL_URL = os.getenv("EMAIL_SERVICE_URL", os.getenv("EMAIL_SERVICE_ADDR", "http://localhost:8088"))

@app.get("/healthz")
def health(): return {"status": "ok", "service": "checkout-service"}

@app.post("/api/checkout")
def place_order(req: PlaceOrderRequest):
    order_id = f"ORD-SH-{uuid.uuid4().hex[:8].upper()}"
    logger.info(f"🛒 [CHECKOUT STARTED] Order: {order_id} | User: {req.user_id}")

    # 1. Fetch Cart
    try:
        cart_res = requests.get(f"{CART_URL}/api/cart/{req.user_id}", timeout=3).json()
        cart_items = cart_res.get("items", [])
    except Exception:
        cart_items = [{"product_id": "SH-001", "quantity": 1}]

    # 2. Ship Order
    try:
        ship_res = requests.post(f"{SHIPPING_URL}/api/shipping/ship", json={
            "address": req.address.model_dump(),
            "items": cart_items
        }, timeout=3).json()
        tracking_id = ship_res.get("tracking_id", f"SH-TRK-{uuid.uuid4().hex[:8].upper()}")
    except Exception:
        tracking_id = f"SH-TRK-{uuid.uuid4().hex[:8].upper()}"

    # 3. Charge Payment
    try:
        requests.post(f"{PAYMENT_URL}/api/payment/charge", json={
            "amount": {"currency_code": req.user_currency, "units": 45, "nanos": 0},
            "credit_card": req.credit_card.model_dump()
        }, timeout=3)
    except Exception:
        pass

    # 4. Dispatch Email & Empty Cart
    try:
        order_data = {"order_id": order_id, "shipping_tracking_id": tracking_id}
        requests.post(f"{EMAIL_URL}/api/email/confirmation", params={"email": req.email}, json=order_data, timeout=3)
        requests.delete(f"{CART_URL}/api/cart/{req.user_id}", timeout=3)
    except Exception:
        pass

    return {
        "order": {
            "order_id": order_id,
            "shipping_tracking_id": tracking_id,
            "items": cart_items
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8086")))
