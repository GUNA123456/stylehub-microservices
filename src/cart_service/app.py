"""
StyleHub - Cart Service
gRPC Microservice managing user shopping carts backed by Redis with item removal & quantity management
"""

from fastapi import FastAPI
from contextlib import asynccontextmanager
import os, json, logging, sys, concurrent.futures, grpc

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from genproto import stylehub_pb2, stylehub_pb2_grpc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CartService")

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
            return json.loads(raw) if raw else []
        except Exception: pass
    return IN_MEMORY_CARTS.get(user_id, [])

def _save_cart(user_id: str, items: list):
    if redis_client:
        try:
            redis_client.set(f"cart:{user_id}", json.dumps(items))
            return
        except Exception: pass
    IN_MEMORY_CARTS[user_id] = items

class CartServicer(stylehub_pb2_grpc.CartServiceServicer):
    def AddItem(self, request, context):
        user_id = request.user_id
        items = _get_cart(user_id)
        found = False
        for i in items:
            if i["product_id"] == request.item.product_id:
                i["quantity"] += request.item.quantity
                found = True
                break
        if not found:
            items.append({"product_id": request.item.product_id, "quantity": request.item.quantity})
        _save_cart(user_id, items)
        return stylehub_pb2.Empty()

    def RemoveItem(self, request, context):
        user_id = request.user_id
        items = _get_cart(user_id)
        filtered = [i for i in items if i["product_id"] != request.product_id]
        _save_cart(user_id, filtered)
        logger.info(f"🛒 Item {request.product_id} removed from cart for user {user_id}")
        return stylehub_pb2.Empty()

    def UpdateItemQuantity(self, request, context):
        user_id = request.user_id
        items = _get_cart(user_id)
        if request.quantity <= 0:
            filtered = [i for i in items if i["product_id"] != request.product_id]
            _save_cart(user_id, filtered)
        else:
            for i in items:
                if i["product_id"] == request.product_id:
                    i["quantity"] = request.quantity
                    break
            _save_cart(user_id, items)
        return stylehub_pb2.Empty()

    def GetCart(self, request, context):
        items = _get_cart(request.user_id)
        pb_items = [stylehub_pb2.CartItem(product_id=i["product_id"], quantity=i["quantity"]) for i in items]
        return stylehub_pb2.Cart(user_id=request.user_id, items=pb_items)

    def EmptyCart(self, request, context):
        _save_cart(request.user_id, [])
        return stylehub_pb2.Empty()

@asynccontextmanager
async def lifespan(app: FastAPI):
    grpc_server = grpc.server(concurrent.futures.ThreadPoolExecutor(max_workers=10))
    stylehub_pb2_grpc.add_CartServiceServicer_to_server(CartServicer(), grpc_server)
    grpc_port = int(os.getenv("GRPC_PORT", "50052"))
    grpc_server.add_insecure_port(f"[::]:{grpc_port}")
    grpc_server.start()
    logger.info(f"⚡ CartService gRPC active on port {grpc_port}")
    yield
    grpc_server.stop(grace=None)

app = FastAPI(title="StyleHub Cart Service", lifespan=lifespan)

@app.get("/healthz")
def health_check():
    return {"status": "ok", "service": "cart-service", "storage": "redis" if redis_client else "in-memory"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8082")))
