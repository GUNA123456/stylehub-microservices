"""
StyleHub - Product Catalog Service
gRPC Microservice managing fashion apparel catalog & search
"""

from fastapi import FastAPI
from contextlib import asynccontextmanager
import os, sys, concurrent.futures, grpc

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from genproto import stylehub_pb2, stylehub_pb2_grpc

PRODUCTS_DB = [
    {"id": "SH-001", "name": "Vintage Denim Jacket", "description": "Classic vintage washed denim jacket with reinforced stitching.", "picture": "/static/img/products/denim-jacket.jpg", "price": (89, 99000000), "cat": ["clothing", "jackets"]},
    {"id": "SH-002", "name": "Urban Streetwear Hoodie", "description": "Heavyweight organic cotton blend hoodie with relaxed fit.", "picture": "/static/img/products/streetwear-hoodie.jpg", "price": (64, 50000000), "cat": ["clothing", "hoodies"]},
    {"id": "SH-003", "name": "Minimalist Leather Sneakers", "description": "Premium Italian leather low-top sneakers.", "picture": "/static/img/products/leather-sneakers.jpg", "price": (120, 0), "cat": ["footwear", "shoes"]},
    {"id": "SH-004", "name": "Tailored Slim-Fit Chinos", "description": "Breathable stretch-cotton chinos.", "picture": "/static/img/products/slim-chinos.jpg", "price": (55, 0), "cat": ["clothing", "pants"]},
    {"id": "SH-005", "name": "Classic Polarized Sunglasses", "description": "UV400 protection polarized lenses.", "picture": "/static/img/products/sunglasses.jpg", "price": (42, 50000000), "cat": ["accessories", "eyewear"]},
    {"id": "SH-006", "name": "Canvas Minimalist Backpack", "description": "Water-resistant canvas backpack with laptop compartment.", "picture": "/static/img/products/backpack.jpg", "price": (78, 0), "cat": ["accessories", "bags"]}
]

def _to_pb_product(p):
    price = stylehub_pb2.Money(currency_code="USD", units=p["price"][0], nanos=p["price"][1])
    return stylehub_pb2.Product(
        id=p["id"], name=p["name"], description=p["description"], picture=p["picture"], price_usd=price, categories=p["cat"]
    )

class ProductCatalogServicer(stylehub_pb2_grpc.ProductCatalogServiceServicer):
    def ListProducts(self, request, context):
        return stylehub_pb2.ListProductsResponse(products=[_to_pb_product(p) for p in PRODUCTS_DB])

    def GetProduct(self, request, context):
        for p in PRODUCTS_DB:
            if p["id"] == request.id:
                return _to_pb_product(p)
        context.set_code(grpc.StatusCode.NOT_FOUND)
        context.set_details(f"Product {request.id} not found")
        return stylehub_pb2.Product()

    def SearchProducts(self, request, context):
        q = request.query.lower()
        matched = [p for p in PRODUCTS_DB if q in p["name"].lower() or q in p["description"].lower() or any(q in c.lower() for c in p["cat"])]
        return stylehub_pb2.SearchProductsResponse(results=[_to_pb_product(p) for p in matched])

@asynccontextmanager
async def lifespan(app: FastAPI):
    grpc_server = grpc.server(concurrent.futures.ThreadPoolExecutor(max_workers=10))
    stylehub_pb2_grpc.add_ProductCatalogServiceServicer_to_server(ProductCatalogServicer(), grpc_server)
    grpc_port = int(os.getenv("GRPC_PORT", "50051"))
    grpc_server.add_insecure_port(f"[::]:{grpc_port}")
    grpc_server.start()
    print(f"⚡ ProductCatalog gRPC server active on port {grpc_port}")
    yield
    grpc_server.stop(grace=None)

app = FastAPI(title="StyleHub Product Catalog Service", lifespan=lifespan)

@app.get("/healthz")
def health_check():
    return {"status": "ok", "service": "product-catalog-service", "grpc_port": os.getenv("GRPC_PORT", "50051")}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8081")))
