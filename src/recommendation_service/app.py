"""
StyleHub - Recommendation Service
Custom Python Microservice providing tailored product recommendations with gRPC Support
"""

from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import os, random, sys, concurrent.futures, grpc

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from genproto import stylehub_pb2, stylehub_pb2_grpc

app = FastAPI(
    title="StyleHub Recommendation Service",
    description="Generates personalized fashion recommendations for StyleHub shoppers",
    version="1.0.0"
)

class RecommendationRequest(BaseModel):
    user_id: str
    product_ids: List[str] = []

class RecommendationResponse(BaseModel):
    product_ids: List[str]

ALL_PRODUCT_IDS = ["SH-001", "SH-002", "SH-003", "SH-004", "SH-005", "SH-006"]

def compute_recommendations(user_ids: str, current_product_ids: List[str]) -> List[str]:
    filtered = [pid for pid in ALL_PRODUCT_IDS if pid not in current_product_ids]
    if not filtered:
        filtered = ALL_PRODUCT_IDS
    sample_size = min(4, len(filtered))
    return random.sample(filtered, sample_size)

class RecommendationServicer(stylehub_pb2_grpc.RecommendationServiceServicer):
    def ListRecommendations(self, request, context):
        recs = compute_recommendations(request.user_id, list(request.product_ids))
        return stylehub_pb2.ListRecommendationsResponse(product_ids=recs)

grpc_server = None

@app.on_event("startup")
def startup_event():
    global grpc_server
    grpc_server = grpc.server(concurrent.futures.ThreadPoolExecutor(max_workers=10))
    stylehub_pb2_grpc.add_RecommendationServiceServicer_to_server(RecommendationServicer(), grpc_server)
    grpc_port = int(os.getenv("GRPC_PORT", "50054"))
    grpc_server.add_insecure_port(f"[::]:{grpc_port}")
    grpc_server.start()
    print(f"RecommendationService gRPC server running on port {grpc_port}")

@app.on_event("shutdown")
def shutdown_event():
    global grpc_server
    if grpc_server:
        grpc_server.stop(grace=None)

@app.get("/healthz")
def health_check():
    return {"status": "ok", "service": "recommendation-service", "grpc_port": os.getenv("GRPC_PORT", "50054")}

@app.post("/api/recommendations", response_model=RecommendationResponse)
def get_recommendations(request: RecommendationRequest):
    recs = compute_recommendations(request.user_id, request.product_ids)
    return RecommendationResponse(product_ids=recs)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8084"))
    uvicorn.run(app, host="0.0.0.0", port=port)
