"""
StyleHub - Recommendation Service
gRPC Microservice providing tailored product recommendations
"""

from fastapi import FastAPI
import os, random, sys, concurrent.futures, grpc

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from genproto import stylehub_pb2, stylehub_pb2_grpc

app = FastAPI(title="StyleHub Recommendation Service")

ALL_PIDS = ["SH-001", "SH-002", "SH-003", "SH-004", "SH-005", "SH-006"]

class RecommendationServicer(stylehub_pb2_grpc.RecommendationServiceServicer):
    def ListRecommendations(self, request, context):
        filtered = [pid for pid in ALL_PIDS if pid not in request.product_ids] or ALL_PIDS
        sample = random.sample(filtered, min(4, len(filtered)))
        return stylehub_pb2.ListRecommendationsResponse(product_ids=sample)

grpc_server = None

@app.on_event("startup")
def startup_event():
    global grpc_server
    grpc_server = grpc.server(concurrent.futures.ThreadPoolExecutor(max_workers=10))
    stylehub_pb2_grpc.add_RecommendationServiceServicer_to_server(RecommendationServicer(), grpc_server)
    grpc_port = int(os.getenv("GRPC_PORT", "50054"))
    grpc_server.add_insecure_port(f"[::]:{grpc_port}")
    grpc_server.start()
    print(f"⚡ RecommendationService gRPC active on port {grpc_port}")

@app.on_event("shutdown")
def shutdown_event():
    if grpc_server: grpc_server.stop(grace=None)

@app.get("/healthz")
def health_check(): return {"status": "ok", "service": "recommendation-service"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8084")))
