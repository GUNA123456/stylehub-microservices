"""
StyleHub - Product Catalog Service
Custom Python Microservice for StyleHub E-Commerce
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import os

app = FastAPI(
    title="StyleHub Product Catalog Service",
    description="Manages fashion apparel, accessories, and catalog search for StyleHub",
    version="1.0.0"
)

class Money(BaseModel):
    currency_code: str = "USD"
    units: int
    nanos: int = 0

class Product(BaseModel):
    id: str
    name: str
    description: str
    picture: str
    price_usd: Money
    categories: List[str]

# Sample StyleHub Fashion Product Catalog Data
PRODUCTS_DB = [
    Product(
        id="SH-001",
        name="Vintage Denim Jacket",
        description="Classic vintage washed denim jacket with reinforced stitching and dual chest pockets.",
        picture="/static/img/products/denim-jacket.jpg",
        price_usd=Money(units=89, nanos=99000000),
        categories=["clothing", "jackets", "outerwear"]
    ),
    Product(
        id="SH-002",
        name="Urban Streetwear Hoodie",
        description="Heavyweight organic cotton blend hoodie featuring a relaxed fit and fleece lining.",
        picture="/static/img/products/streetwear-hoodie.jpg",
        price_usd=Money(units=64, nanos=50000000),
        categories=["clothing", "hoodies", "streetwear"]
    ),
    Product(
        id="SH-003",
        name="Minimalist Leather Sneakers",
        description="Premium Italian leather low-top sneakers with cushioned insoles and durable rubber soles.",
        picture="/static/img/products/leather-sneakers.jpg",
        price_usd=Money(units=120, nanos=0),
        categories=["footwear", "shoes", "sneakers"]
    ),
    Product(
        id="SH-004",
        name="Tailored Slim-Fit Chinos",
        description="Breathable stretch-cotton chinos suitable for formal and casual wear.",
        picture="/static/img/products/slim-chinos.jpg",
        price_usd=Money(units=55, nanos=0),
        categories=["clothing", "pants", "casual"]
    ),
    Product(
        id="SH-005",
        name="Classic Polarized Sunglasses",
        description="UV400 protection polarized lenses with lightweight acetate frames.",
        picture="/static/img/products/sunglasses.jpg",
        price_usd=Money(units=42, nanos=50000000),
        categories=["accessories", "eyewear"]
    ),
    Product(
        id="SH-006",
        name="Canvas Minimalist Backpack",
        description="Water-resistant canvas backpack with dedicated 15-inch laptop compartment.",
        picture="/static/img/products/backpack.jpg",
        price_usd=Money(units=78, nanos=0),
        categories=["accessories", "bags"]
    )
]

@app.get("/healthz")
def health_check():
    return {"status": "ok", "service": "product-catalog-service"}

@app.get("/api/products", response_model=List[Product])
def list_products():
    """Retrieve all products in the catalog."""
    return PRODUCTS_DB

@app.get("/api/products/{product_id}", response_model=Product)
def get_product(product_id: str):
    """Retrieve a specific product by ID."""
    for product in PRODUCTS_DB:
        if product.id == product_id:
            return product
    raise HTTPException(status_code=404, detail=f"Product with ID '{product_id}' not found")

@app.get("/api/search", response_model=List[Product])
def search_products(query: str):
    """Search products by name, category, or description."""
    q = query.lower()
    results = [
        p for p in PRODUCTS_DB
        if q in p.name.lower() or q in p.description.lower() or any(q in c.lower() for c in p.categories)
    ]
    return results

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8081"))
    uvicorn.run(app, host="0.0.0.0", port=port)
