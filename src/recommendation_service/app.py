"""
StyleHub - Recommendation Service
Clean FastAPI Microservice providing product recommendations
"""

from fastapi import FastAPI
from typing import List
import os, random

app = FastAPI(title="StyleHub Recommendation Service")

ALL_PIDS = ["SH-001", "SH-002", "SH-003", "SH-004", "SH-005", "SH-006"]

@app.get("/healthz")
def health(): return {"status": "ok", "service": "recommendation-service"}

@app.post("/api/recommendations")
def get_recommendations(user_id: str = "user-demo-123", product_ids: List[str] = []):
    filtered = [pid for pid in ALL_PIDS if pid not in product_ids] or ALL_PIDS
    sample = random.sample(filtered, min(4, len(filtered)))
    return {"product_ids": sample}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8084")))
