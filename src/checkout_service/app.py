"""
StyleHub - Checkout Orchestrator Service
Clean FastAPI Microservice orchestrating Cart, Shipping, Payment, and Email REST calls
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os, uuid, logging, requests

# Inline data models (self-contained, no shared module dependency)
class Address(BaseModel):
    street_address: str
    city: str
    state: str
    country: str = "United States"
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CheckoutService")

app = FastAPI(title="StyleHub Checkout Service")

CART_URL = os.getenv("CART_SERVICE_URL", os.getenv("CART_SERVICE_ADDR", "http://localhost:8082"))
SHIPPING_URL = os.getenv("SHIPPING_SERVICE_URL", os.getenv("SHIPPING_SERVICE_ADDR", "http://localhost:8085"))
PAYMENT_URL = os.getenv("PAYMENT_SERVICE_URL", os.getenv("PAYMENT_SERVICE_ADDR", "http://localhost:8089"))
EMAIL_URL = os.getenv("EMAIL_SERVICE_URL", os.getenv("EMAIL_SERVICE_ADDR", "http://localhost:8088"))

import obs  # /metrics + dependency-edge counters + optional OTel tracing (Phase 1)
obs.install(app, "stylehub-checkout-service", dependencies={
    "cart": CART_URL, "shipping": SHIPPING_URL, "payment": PAYMENT_URL, "email": EMAIL_URL,
})

@app.get("/healthz")
def health(): return {"status": "ok", "service": "checkout-service"}

# Phase 1 failure policy. Round 1 masked every dependency failure: a dead cart produced
# an invented one-item cart, a dead shipping service produced an invented tracking ID,
# and a dead payment service was silently skipped — an order could "succeed" with every
# dependency down, so no fault ever propagated and cascades were unobservable.
#
# Now: cart, shipping and payment are CRITICAL — their failure fails the order with a
# 502 naming the broken dependency. Email and cart-emptying are OPTIONAL — the order
# survives, but the failure is counted (service_dependency_errors_total) and reported
# in the response instead of being swallowed. This is a documented design decision,
# not resilience engineering: the research needs failures to be observable.
def _call_critical(dependency, fn):
    """Run one critical outbound call; translate any failure into a 502 that names
    the dependency, so the caller (and the metrics) see exactly what broke."""
    try:
        resp = fn()
        resp.raise_for_status()
        return resp
    except requests.RequestException as e:
        logger.error(f"CRITICAL dependency '{dependency}' failed: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"{dependency} unavailable ({type(e).__name__}) — order not placed",
        )


@app.post("/api/checkout")
def place_order(req: PlaceOrderRequest):
    order_id = f"ORD-SH-{uuid.uuid4().hex[:8].upper()}"
    logger.info(f"🛒 [CHECKOUT STARTED] Order: {order_id} | User: {req.user_id}")

    # 1. Fetch Cart — CRITICAL (an order for an unknown cart is not an order)
    cart_res = _call_critical("cart-service", lambda: requests.get(
        f"{CART_URL}/api/cart/{req.user_id}", timeout=3))
    cart_items = cart_res.json().get("items", [])
    if not cart_items:
        raise HTTPException(status_code=400, detail="cart is empty — nothing to order")

    # 2. Ship Order — CRITICAL (no shipment booked means nothing will arrive)
    ship_res = _call_critical("shipping-service", lambda: requests.post(
        f"{SHIPPING_URL}/api/shipping/ship",
        json={"address": req.address.model_dump(), "items": cart_items}, timeout=3))
    tracking_id = ship_res.json().get("tracking_id", f"SH-TRK-{uuid.uuid4().hex[:8].upper()}")

    # 3. Charge Payment — CRITICAL (an unpaid order must never report success)
    _call_critical("payment-service", lambda: requests.post(
        f"{PAYMENT_URL}/api/payment/charge",
        json={"amount": {"currency_code": req.user_currency, "units": 45, "nanos": 0},
              "credit_card": req.credit_card.model_dump()}, timeout=3))

    # 4. Email & empty cart — OPTIONAL: degrade, but visibly (counted + reported)
    email_sent = True
    try:
        requests.post(f"{EMAIL_URL}/api/email/confirmation", params={"email": req.email},
                      json={"order_id": order_id, "shipping_tracking_id": tracking_id},
                      timeout=3).raise_for_status()
    except requests.RequestException as e:
        email_sent = False
        logger.warning(f"optional dependency 'email-service' failed: {type(e).__name__}")
    try:
        requests.delete(f"{CART_URL}/api/cart/{req.user_id}", timeout=3)
    except requests.RequestException as e:
        logger.warning(f"post-order cart empty failed: {type(e).__name__}")

    return {
        "order": {
            "order_id": order_id,
            "shipping_tracking_id": tracking_id,
            "items": cart_items,
            # Degradation is reported, never hidden: a caller (and the dataset labeller)
            # can distinguish a full success from a success with a failed confirmation.
            "email_sent": email_sent
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8086")), timeout_keep_alive=120)
