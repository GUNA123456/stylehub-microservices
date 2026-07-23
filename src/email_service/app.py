"""
StyleHub - Email Service
gRPC Microservice for order receipt & confirmation notifications
"""

from fastapi import FastAPI
from contextlib import asynccontextmanager
import os, logging, sys, concurrent.futures, grpc

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from genproto import stylehub_pb2, stylehub_pb2_grpc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EmailService")

class EmailServicer(stylehub_pb2_grpc.EmailServiceServicer):
    def SendOrderConfirmation(self, request, context):
        order_id = request.order.order_id if request.order else "UNKNOWN"
        tracking = request.order.shipping_tracking_id if request.order else "N/A"
        logger.info(f"📧 [gRPC EMAIL DISPATCH] To: {request.email} | Order ID: {order_id} | Tracking: {tracking}")
        return stylehub_pb2.Empty()

@asynccontextmanager
async def lifespan(app: FastAPI):
    grpc_server = grpc.server(concurrent.futures.ThreadPoolExecutor(max_workers=10))
    stylehub_pb2_grpc.add_EmailServiceServicer_to_server(EmailServicer(), grpc_server)
    grpc_port = int(os.getenv("GRPC_PORT", "50058"))
    grpc_server.add_insecure_port(f"[::]:{grpc_port}")
    grpc_server.start()
    logger.info(f"⚡ EmailService gRPC active on port {grpc_port}")
    yield
    grpc_server.stop(grace=None)

app = FastAPI(title="StyleHub Email Service", lifespan=lifespan)

@app.get("/healthz")
def health_check(): return {"status": "ok", "service": "email-service"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8088")))
