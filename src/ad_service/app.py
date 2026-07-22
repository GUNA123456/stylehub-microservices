"""
StyleHub - Ad Service
Custom Python Microservice serving targeted advertisements with gRPC Support
"""

from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import os, random, sys, concurrent.futures, grpc

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from genproto import stylehub_pb2, stylehub_pb2_grpc

app = FastAPI(
    title="StyleHub Ad Service",
    description="Delivers contextual fashion advertisements across StyleHub pages",
    version="1.0.0"
)

class Ad(BaseModel):
    redirect_url: str
    text: str

class AdRequest(BaseModel):
    context_keys: List[str] = []

class AdResponse(BaseModel):
    ads: List[Ad]

ADS_DATABASE = {
    "clothing": [
        Ad(redirect_url="/product/SH-001", text="🔥 Summer Sale: Up to 40% OFF Denim Jackets!"),
        Ad(redirect_url="/product/SH-002", text="✨ Upgrade your style with our Organic Streetwear collection.")
    ],
    "footwear": [
        Ad(redirect_url="/product/SH-003", text="👟 Step in style: Premium Italian Leather Sneakers now in stock.")
    ],
    "accessories": [
        Ad(redirect_url="/product/SH-005", text="🕶️ Protect your eyes with Polarized Acetate Sunglasses."),
        Ad(redirect_url="/product/SH-006", text="🎒 Water-resistant Minimalist Backpacks for everyday travel.")
    ]
}

DEFAULT_ADS = [
    Ad(redirect_url="/", text="🎉 Free Shipping on orders over $75 with code STYLEHUB2026!")
]

def fetch_ads(context_keys: List[str]) -> List[dict]:
    matched = []
    for key in context_keys:
        k = key.lower()
        if k in ADS_DATABASE:
            matched.extend([{"redirect_url": a.redirect_url, "text": a.text} for a in ADS_DATABASE[k]])
    if not matched:
        matched = [{"redirect_url": a.redirect_url, "text": a.text} for a in DEFAULT_ADS]
    return matched

class AdServicer(stylehub_pb2_grpc.AdServiceServicer):
    def GetAds(self, request, context):
        matched = fetch_ads(list(request.context_keys))
        pb_ads = [stylehub_pb2.Ad(redirect_url=a["redirect_url"], text=a["text"]) for a in matched]
        return stylehub_pb2.AdResponse(ads=pb_ads)

grpc_server = None

@app.on_event("startup")
def startup_event():
    global grpc_server
    grpc_server = grpc.server(concurrent.futures.ThreadPoolExecutor(max_workers=10))
    stylehub_pb2_grpc.add_AdServiceServicer_to_server(AdServicer(), grpc_server)
    grpc_port = int(os.getenv("GRPC_PORT", "50057"))
    grpc_server.add_insecure_port(f"[::]:{grpc_port}")
    grpc_server.start()
    print(f"AdService gRPC server running on port {grpc_port}")

@app.on_event("shutdown")
def shutdown_event():
    global grpc_server
    if grpc_server:
        grpc_server.stop(grace=None)

@app.get("/healthz")
def health_check():
    return {"status": "ok", "service": "ad-service", "grpc_port": os.getenv("GRPC_PORT", "50057")}

@app.post("/api/ads", response_model=AdResponse)
def get_ads(request: AdRequest):
    matched = fetch_ads(request.context_keys)
    return AdResponse(ads=[Ad(**a) for a in matched])

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8087"))
    uvicorn.run(app, host="0.0.0.0", port=port)
