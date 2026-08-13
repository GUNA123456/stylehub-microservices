"""
StyleHub - Cart Service
Clean FastAPI Microservice managing user shopping carts backed by Redis
"""

from fastapi import FastAPI
from pydantic import BaseModel
import os, json, logging

import depgraph  # observes outbound calls so the dependency graph can be discovered, not declared
depgraph.install()

# Inline data models (self-contained, no shared module dependency)
class CartItem(BaseModel):
    product_id: str
    quantity: int

class AddItemRequest(BaseModel):
    user_id: str
    item: CartItem

class UpdateQuantityRequest(BaseModel):
    user_id: str
    product_id: str
    quantity: int

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CartService")

app = FastAPI(title="StyleHub Cart Service")

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

redis_client = None
IN_MEMORY_CARTS = {}

try:
    import redis
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, socket_connect_timeout=2)
    r.ping()
    redis_client = r
    logger.info(f"⚡ Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
except Exception as e:
    logger.warning(f"⚠️ Redis unavailable ({e}). Using in-memory fallback.")

def _get_cart(user_id: str):
    if redis_client:
        try:
            raw = redis_client.get(f"cart:{user_id}")
            # Redis is reached over its own protocol, not HTTP, so the requests patch in
            # depgraph.install() cannot see it. Recorded explicitly to keep the cart->redis
            # edge in the discovered graph.
            depgraph.record("stylehub-redis")
            return json.loads(raw) if raw else []
        except Exception: pass
    return IN_MEMORY_CARTS.get(user_id, [])

def _save_cart(user_id: str, items: list):
    if redis_client:
        try:
            redis_client.set(f"cart:{user_id}", json.dumps(items))
            depgraph.record("stylehub-redis")
            return
        except Exception: pass
    IN_MEMORY_CARTS[user_id] = items

@app.get("/healthz")
def health(): return {"status": "ok", "service": "cart-service", "storage": "redis" if redis_client else "in-memory"}

@app.get("/api/cart/{user_id}")
def get_cart(user_id: str):
    items = _get_cart(user_id)
    return {"user_id": user_id, "items": items}

@app.post("/api/cart/add")
def add_item(req: AddItemRequest):
    items = _get_cart(req.user_id)
    found = False
    for i in items:
        if i["product_id"] == req.item.product_id:
            i["quantity"] += req.item.quantity
            found = True
            break
    if not found:
        items.append({"product_id": req.item.product_id, "quantity": req.item.quantity})
    _save_cart(req.user_id, items)
    return {"status": "success"}

@app.post("/api/cart/update-quantity")
def update_quantity(req: UpdateQuantityRequest):
    items = _get_cart(req.user_id)
    if req.quantity <= 0:
        items = [i for i in items if i["product_id"] != req.product_id]
    else:
        for i in items:
            if i["product_id"] == req.product_id:
                i["quantity"] = req.quantity
                break
    _save_cart(req.user_id, items)
    return {"status": "success"}

@app.delete("/api/cart/{user_id}/item/{product_id}")
def remove_item(user_id: str, product_id: str):
    items = _get_cart(user_id)
    filtered = [i for i in items if i["product_id"] != product_id]
    _save_cart(user_id, filtered)
    return {"status": "success"}

@app.delete("/api/cart/{user_id}")
def empty_cart(user_id: str):
    _save_cart(user_id, [])
    return {"status": "success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8082")), timeout_keep_alive=120)
