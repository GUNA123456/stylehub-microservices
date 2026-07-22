"""
StyleHub - Email Notification Service
Custom Python Microservice managing order receipt & confirmation notifications
"""

from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
import os, logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EmailService")

app = FastAPI(
    title="StyleHub Email Service",
    description="Sends automated email confirmations and order updates",
    version="1.0.0"
)

class SendOrderConfirmationRequest(BaseModel):
    email: str
    order_id: str
    tracking_id: str
    total_amount: str

@app.get("/healthz")
def health_check():
    return {"status": "ok", "service": "email-service"}

@app.post("/api/email/order-confirmation")
def send_order_confirmation(request: SendOrderConfirmationRequest):
    """Simulates sending an order confirmation email to the user."""
    logger.info(
        f"📧 [EMAIL SENT] To: {request.email} | Order ID: {request.order_id} | "
        f"Tracking: {request.tracking_id} | Total: {request.total_amount}"
    )
    return {
        "status": "success",
        "message": f"Order confirmation email dispatched to {request.email}",
        "order_id": request.order_id
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8087"))
    uvicorn.run(app, host="0.0.0.0", port=port)
