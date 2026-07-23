"""
StyleHub - Payment Processing Service
gRPC Microservice for credit card validation & transactions
"""

from fastapi import FastAPI
import os, uuid, logging, sys, concurrent.futures, grpc

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from genproto import stylehub_pb2, stylehub_pb2_grpc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PaymentService")

app = FastAPI(title="StyleHub Payment Service")

class PaymentServicer(stylehub_pb2_grpc.PaymentServiceServicer):
    def Charge(self, request, context):
        card_num = request.credit_card.credit_card_number.replace("-", "").replace(" ", "")
        if len(card_num) < 13 or not card_num.isdigit():
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("Invalid credit card format")
            return stylehub_pb2.ChargeResponse()
        
        tx_id = f"TX-SH-{uuid.uuid4().hex[:12].upper()}"
        logger.info(f"💳 [PAYMENT SUCCESS] Transaction {tx_id} charged {request.amount.units} {request.amount.currency_code}")
        return stylehub_pb2.ChargeResponse(transaction_id=tx_id)

grpc_server = None

@app.on_event("startup")
def startup_event():
    global grpc_server
    grpc_server = grpc.server(concurrent.futures.ThreadPoolExecutor(max_workers=10))
    stylehub_pb2_grpc.add_PaymentServiceServicer_to_server(PaymentServicer(), grpc_server)
    grpc_port = int(os.getenv("GRPC_PORT", "50059"))
    grpc_server.add_insecure_port(f"[::]:{grpc_port}")
    grpc_server.start()
    logger.info(f"⚡ PaymentService gRPC active on port {grpc_port}")

@app.on_event("shutdown")
def shutdown_event():
    if grpc_server: grpc_server.stop(grace=None)

@app.get("/healthz")
def health_check(): return {"status": "ok", "service": "payment-service"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8089")))
