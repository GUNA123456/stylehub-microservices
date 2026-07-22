"""
StyleHub - Payment Processing Service
Custom Python Microservice for credit card validation & transactions with gRPC Support
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os, uuid, logging, sys, concurrent.futures, grpc

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from genproto import stylehub_pb2, stylehub_pb2_grpc

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

def process_charge(card_number: str, amount_units: int, amount_nanos: int, currency: str) -> str:
    card_num = card_number.replace("-", "").replace(" ", "")
    if len(card_num) < 13 or not card_num.isdigit():
        raise ValueError("Invalid credit card number format")
    tx_id = f"TX-SH-{uuid.uuid4().hex[:12].upper()}"
    logger.info(f"💳 [PAYMENT SUCCESS] Transaction {tx_id} charged {amount_units}.{amount_nanos} {currency}")
    return tx_id

class PaymentServicer(stylehub_pb2_grpc.PaymentServiceServicer):
    def Charge(self, request, context):
        try:
            tx_id = process_charge(
                request.credit_card.credit_card_number,
                request.amount.units,
                request.amount.nanos,
                request.amount.currency_code
            )
            return stylehub_pb2.ChargeResponse(transaction_id=tx_id)
        except Exception as e:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(e))
            return stylehub_pb2.ChargeResponse()

grpc_server = None

@app.on_event("startup")
def startup_event():
    global grpc_server
    grpc_server = grpc.server(concurrent.futures.ThreadPoolExecutor(max_workers=10))
    stylehub_pb2_grpc.add_PaymentServiceServicer_to_server(PaymentServicer(), grpc_server)
    grpc_port = int(os.getenv("GRPC_PORT", "50059"))
    grpc_server.add_insecure_port(f"[::]:{grpc_port}")
    grpc_server.start()
    print(f"PaymentService gRPC server running on port {grpc_port}")

@app.on_event("shutdown")
def shutdown_event():
    global grpc_server
    if grpc_server:
        grpc_server.stop(grace=None)

@app.get("/healthz")
def health_check():
    return {"status": "ok", "service": "payment-service", "grpc_port": os.getenv("GRPC_PORT", "50059")}

@app.post("/api/payment/charge", response_model=ChargeResponse)
def charge(request: ChargeRequest):
    try:
        tx_id = process_charge(
            request.credit_card.credit_card_number,
            request.amount.units,
            request.amount.nanos,
            request.amount.currency_code
        )
        return ChargeResponse(transaction_id=tx_id, status="CHARGED")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8089"))
    uvicorn.run(app, host="0.0.0.0", port=port)
