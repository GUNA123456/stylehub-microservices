"""
StyleHub - Email Notification Service
Custom Python Microservice managing order receipt & confirmation notifications with gRPC Support
"""

from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
import os, logging, sys, concurrent.futures, grpc

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from genproto import stylehub_pb2, stylehub_pb2_grpc

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

class EmailServicer(stylehub_pb2_grpc.EmailServiceServicer):
    def SendOrderConfirmation(self, request, context):
        order_id = request.order.order_id if request.order else "UNKNOWN"
        tracking = request.order.shipping_tracking_id if request.order else "N/A"
        logger.info(f"📧 [gRPC EMAIL SENT] To: {request.email} | Order ID: {order_id} | Tracking: {tracking}")
        return stylehub_pb2.Empty()

grpc_server = None

@app.on_event("startup")
def startup_event():
    global grpc_server
    grpc_server = grpc.server(concurrent.futures.ThreadPoolExecutor(max_workers=10))
    stylehub_pb2_grpc.add_EmailServiceServicer_to_server(EmailServicer(), grpc_server)
    grpc_port = int(os.getenv("GRPC_PORT", "50058"))
    grpc_server.add_insecure_port(f"[::]:{grpc_port}")
    grpc_server.start()
    logger.info(f"EmailService gRPC server running on port {grpc_port}")

@app.on_event("shutdown")
def shutdown_event():
    global grpc_server
    if grpc_server:
        grpc_server.stop(grace=None)

@app.get("/healthz")
def health_check():
    return {"status": "ok", "service": "email-service", "grpc_port": os.getenv("GRPC_PORT", "50058")}

@app.post("/api/email/order-confirmation")
def send_order_confirmation(request: SendOrderConfirmationRequest):
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
    port = int(os.getenv("PORT", "8088"))
    uvicorn.run(app, host="0.0.0.0", port=port)
