"""
StyleHub - Ad Service
gRPC Microservice serving targeted advertisements
"""

from fastapi import FastAPI
import os, sys, concurrent.futures, grpc

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from genproto import stylehub_pb2, stylehub_pb2_grpc

app = FastAPI(title="StyleHub Ad Service")

ADS_DB = {
    "clothing": [stylehub_pb2.Ad(redirect_url="/product/SH-001", text="🔥 Summer Sale: Up to 40% OFF Denim Jackets!")],
    "footwear": [stylehub_pb2.Ad(redirect_url="/product/SH-003", text="👟 Premium Italian Leather Sneakers in stock.")],
    "accessories": [stylehub_pb2.Ad(redirect_url="/product/SH-005", text="🕶️ Polarized Acetate Sunglasses.")]
}

DEFAULT_ADS = [stylehub_pb2.Ad(redirect_url="/", text="🎉 Free Shipping on orders over $50 with code STYLEHUB2026!")]

class AdServicer(stylehub_pb2_grpc.AdServiceServicer):
    def GetAds(self, request, context):
        matched = []
        for k in request.context_keys:
            if k.lower() in ADS_DB:
                matched.extend(ADS_DB[k.lower()])
        return stylehub_pb2.AdResponse(ads=matched or DEFAULT_ADS)

grpc_server = None

@app.on_event("startup")
def startup_event():
    global grpc_server
    grpc_server = grpc.server(concurrent.futures.ThreadPoolExecutor(max_workers=10))
    stylehub_pb2_grpc.add_AdServiceServicer_to_server(AdServicer(), grpc_server)
    grpc_port = int(os.getenv("GRPC_PORT", "50057"))
    grpc_server.add_insecure_port(f"[::]:{grpc_port}")
    grpc_server.start()
    print(f"⚡ AdService gRPC active on port {grpc_port}")

@app.on_event("shutdown")
def shutdown_event():
    if grpc_server: grpc_server.stop(grace=None)

@app.get("/healthz")
def health_check(): return {"status": "ok", "service": "ad-service"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8087")))
