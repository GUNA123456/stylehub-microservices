"""
StyleHub - Recommendation Service
Custom Python Microservice providing tailored product recommendations
"""

from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import os, random

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

@app.get("/healthz")
def health_check():
    return {"status": "ok", "service": "recommendation-service"}

@app.post("/api/recommendations", response_model=RecommendationResponse)
def get_recommendations(request: RecommendationRequest):
    """Generates a list of recommended product IDs excluding those currently viewed/purchased."""
    filtered = [pid for pid in ALL_PRODUCT_IDS if pid not in request.product_ids]
    if not filtered:
        filtered = ALL_PRODUCT_IDS

    # Pick up to 4 recommendations
    sample_size = min(4, len(filtered))
    recommended = random.sample(filtered, sample_size)
    return RecommendationResponse(product_ids=recommended)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8084"))
    uvicorn.run(app, host="0.0.0.0", port=port)
