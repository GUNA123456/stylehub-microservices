"""
StyleHub - Shipping Service
gRPC Microservice calculating shipping rates & tracking
"""

from fastapi import FastAPI
from contextlib import asynccontextmanager
import os, uuid, sys, concurrent.futures, grpc

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from genproto import stylehub_pb2, stylehub_pb2_grpc

class ShippingServicer(stylehub_pb2_grpc.ShippingServiceServicer):
    def GetQuote(self, request, context):
        total_items = sum(item.quantity for item in request.items)
        cost = 8.99 + (total_items * 1.50)
        units, nanos = int(cost), int((cost - int(cost)) * 1e9)
        return stylehub_pb2.GetQuoteResponse(cost_usd=stylehub_pb2.Money(currency_code="USD", units=units, nanos=nanos))

    def ShipOrder(self, request, context):
        tracking_code = f"SH-TRK-{uuid.uuid4().hex[:10].upper()}"
        return stylehub_pb2.ShipOrderResponse(tracking_id=tracking_code)

@asynccontextmanager
async def lifespan(app: FastAPI):
    grpc_server = grpc.server(concurrent.futures.ThreadPoolExecutor(max_workers=10))
    stylehub_pb2_grpc.add_ShippingServiceServicer_to_server(ShippingServicer(), grpc_server)
    grpc_port = int(os.getenv("GRPC_PORT", "50055"))
    grpc_server.add_insecure_port(f"[::]:{grpc_port}")
    grpc_server.start()
    print(f"⚡ ShippingService gRPC active on port {grpc_port}")
    yield
    grpc_server.stop(grace=None)

app = FastAPI(title="StyleHub Shipping Service", lifespan=lifespan)

@app.get("/healthz")
def health_check(): return {"status": "ok", "service": "shipping-service"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8085")))
