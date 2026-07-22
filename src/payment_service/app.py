"""
StyleHub - Payment Processing Service
Custom Python Microservice for credit card validation & transactions
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os, uuid, logging

logger = logging.getLogger("PaymentService")

app = FastAPI(
    title="StyleHub Payment Service",
    description="Processes payments and handles credit card transactions for StyleHub",
    version="1.0.0"
)

class CreditCardInfo(BaseModel):
    credit_card_number: str
    credit_card_cvv: int
    credit_card_expiration_year: int
    credit_card_expiration_month: int

class Money(BaseModel):
    currency_code: str = "USD"
    units: int
    nanos: int = 0

class ChargeRequest(BaseModel):
    amount: Money
    credit_card: CreditCardInfo

class ChargeResponse(BaseModel):
    transaction_id: str
    status: str

@app.get("/healthz")
def health_check():
    return {"status": "ok", "service": "payment-service"}

@app.post("/api/payment/charge", response_model=ChargeResponse)
def charge(request: ChargeRequest):
    """Validates credit card format and simulates transaction processing."""
    card_num = request.credit_card.credit_card_number.replace("-", "").replace(" ", "")
    
    if len(card_num) < 13 or not card_num.isdigit():
        raise HTTPException(status_code=400, detail="Invalid credit card number format")

    tx_id = f"TX-SH-{uuid.uuid4().hex[:12].upper()}"
    logger.info(f"💳 [PAYMENT SUCCESS] Transaction {tx_id} charged {request.amount.units}.{request.amount.nanos} {request.amount.currency_code}")
    
    return ChargeResponse(
        transaction_id=tx_id,
        status="CHARGED"
    )

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8088"))
    uvicorn.run(app, host="0.0.0.0", port=port)
