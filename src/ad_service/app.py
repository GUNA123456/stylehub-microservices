"""
StyleHub - Ad Service
Custom Python Microservice serving targeted advertisements
"""

from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import os, random

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

@app.get("/healthz")
def health_check():
    return {"status": "ok", "service": "ad-service"}

@app.post("/api/ads", response_model=AdResponse)
def get_ads(request: AdRequest):
    """Returns targeted ads based on context keys or default promotions."""
    matched_ads = []
    for key in request.context_keys:
        k = key.lower()
        if k in ADS_DATABASE:
            matched_ads.extend(ADS_DATABASE[k])

    if not matched_ads:
        matched_ads = DEFAULT_ADS

    return AdResponse(ads=matched_ads)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8085"))
    uvicorn.run(app, host="0.0.0.0", port=port)
