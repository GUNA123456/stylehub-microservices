"""
StyleHub - Cart Service
Custom Python Microservice managing user shopping carts with Redis Storage
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict
import os, json, logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CartService")

app = FastAPI(
    title="StyleHub Cart Service",
    description="Manages active shopping carts for StyleHub users backed by Redis",
    version="1.0.0"
)

class CartItem(BaseModel):
    product_id: str
    quantity: int

class AddItemRequest(BaseModel):
    user_id: str
    item: CartItem

class Cart(BaseModel):
    user_id: str
    items: List[CartItem]

# Redis Setup with In-Memory Fallback
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

redis_client = None
IN_MEMORY_CARTS: Dict[str, List[dict]] = {}

try:
    import redis
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, socket_connect_timeout=2)
    r.ping()
    redis_client = r
    logger.info(f"⚡ Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
except Exception as e:
    logger.warning(f"⚠️ Redis connection failed ({e}). Falling back to in-memory store.")
    redis_client = None

def _get_user_cart_items(user_id: str) -> List[dict]:
    if redis_client:
        try:
            raw = redis_client.get(f"cart:{user_id}")
            if raw:
                return json.loads(raw)
            return []
        except Exception as e:
            logger.error(f"Redis read error: {e}")
    return IN_MEMORY_CARTS.get(user_id, [])

def _save_user_cart_items(user_id: str, items: List[dict]):
    if redis_client:
        try:
            redis_client.set(f"cart:{user_id}", json.dumps(items))
            return
        except Exception as e:
            logger.error(f"Redis write error: {e}")
    IN_MEMORY_CARTS[user_id] = items

@app.get("/healthz")
def health_check():
    redis_status = "connected" if redis_client else "in-memory-fallback"
    return {"status": "ok", "service": "cart-service", "storage": redis_status}

@app.post("/api/cart/items")
def add_item(request: AddItemRequest):
    """Add an item to a user's shopping cart in Redis."""
    user_id = request.user_id
    item_dict = request.item.dict()

    items = _get_user_cart_items(user_id)

    # Check if product exists in cart, increment quantity
    found = False
    for existing in items:
        if existing["product_id"] == item_dict["product_id"]:
            existing["quantity"] += item_dict["quantity"]
            found = True
            break

    if not found:
        items.append(item_dict)

    _save_user_cart_items(user_id, items)
    logger.info(f"🛒 Item added to cart for user {user_id}: {item_dict}")
    return {"status": "success", "user_id": user_id, "cart": items}

@app.get("/api/cart/{user_id}", response_model=Cart)
def get_cart(user_id: str):
    """Retrieve all items in a user's cart from Redis."""
    raw_items = _get_user_cart_items(user_id)
    cart_items = [CartItem(**item) for item in raw_items]
    return Cart(user_id=user_id, items=cart_items)

@app.delete("/api/cart/{user_id}")
def empty_cart(user_id: str):
    """Empty all items from a user's cart in Redis."""
    if redis_client:
        try:
            redis_client.delete(f"cart:{user_id}")
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
    IN_MEMORY_CARTS[user_id] = []
    logger.info(f"🗑️ Cart cleared for user {user_id}")
    return {"status": "success", "message": f"Cart cleared for user '{user_id}'"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8082"))
    uvicorn.run(app, host="0.0.0.0", port=port)
