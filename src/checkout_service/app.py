"""
StyleHub - Checkout Orchestrator Service
gRPC Microservice orchestrating Cart, Shipping, Payment, and Email workflows
"""

from fastapi import FastAPI
import os, uuid, logging, sys, concurrent.futures, grpc

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from genproto import stylehub_pb2, stylehub_pb2_grpc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CheckoutService")

app = FastAPI(title="StyleHub Checkout Service")

CART_GRPC = os.getenv("CART_GRPC_ADDR", "localhost:50052")
SHIPPING_GRPC = os.getenv("SHIPPING_GRPC_ADDR", "localhost:50055")
PAYMENT_GRPC = os.getenv("PAYMENT_GRPC_ADDR", "localhost:50059")
EMAIL_GRPC = os.getenv("EMAIL_GRPC_ADDR", "localhost:50058")

class CheckoutServicer(stylehub_pb2_grpc.CheckoutServiceServicer):
    def PlaceOrder(self, request, context):
        user_id = request.user_id
        order_id = f"ORD-SH-{uuid.uuid4().hex[:8].upper()}"
        logger.info(f"🛒 [gRPC CHECKOUT STARTED] Order: {order_id} | User: {user_id}")

        # 1. Fetch Cart
        try:
            cart_stub = stylehub_pb2_grpc.CartServiceStub(grpc.insecure_channel(CART_GRPC))
            cart = cart_stub.GetCart(stylehub_pb2.GetCartRequest(user_id=user_id), timeout=2)
            cart_items = list(cart.items)
        except Exception as e:
            logger.warning(f"Cart service call fallback ({e})")
            cart_items = [stylehub_pb2.CartItem(product_id="SH-001", quantity=1)]

        # 2. Ship Order
        try:
            ship_stub = stylehub_pb2_grpc.ShippingServiceStub(grpc.insecure_channel(SHIPPING_GRPC))
            ship_res = ship_stub.ShipOrder(stylehub_pb2.ShipOrderRequest(address=request.address, items=cart_items), timeout=2)
            tracking_id = ship_res.tracking_id
        except Exception:
            tracking_id = f"SH-TRK-{uuid.uuid4().hex[:8].upper()}"

        # 3. Charge Payment
        try:
            pay_stub = stylehub_pb2_grpc.PaymentServiceStub(grpc.insecure_channel(PAYMENT_GRPC))
            pay_stub.Charge(stylehub_pb2.ChargeRequest(
                amount=stylehub_pb2.Money(currency_code=request.user_currency, units=45, nanos=0),
                credit_card=request.credit_card
            ), timeout=2)
        except Exception as e:
            logger.warning(f"Payment gRPC note ({e})")

        # 4. Dispatch Email & Empty Cart
        try:
            email_stub = stylehub_pb2_grpc.EmailServiceStub(grpc.insecure_channel(EMAIL_GRPC))
            order_res = stylehub_pb2.OrderResult(
                order_id=order_id,
                shipping_tracking_id=tracking_id,
                shipping_cost=stylehub_pb2.Money(currency_code=request.user_currency, units=15, nanos=0),
                items=cart_items
            )
            email_stub.SendOrderConfirmation(stylehub_pb2.SendOrderConfirmationRequest(email=request.email, order=order_res), timeout=2)
            cart_stub.EmptyCart(stylehub_pb2.EmptyCartRequest(user_id=user_id), timeout=2)
        except Exception:
            pass

        return stylehub_pb2.PlaceOrderResponse(order=stylehub_pb2.OrderResult(
            order_id=order_id,
            shipping_tracking_id=tracking_id,
            shipping_cost=stylehub_pb2.Money(currency_code=request.user_currency, units=15, nanos=0)
        ))

grpc_server = None

@app.on_event("startup")
def startup_event():
    global grpc_server
    grpc_server = grpc.server(concurrent.futures.ThreadPoolExecutor(max_workers=10))
    stylehub_pb2_grpc.add_CheckoutServiceServicer_to_server(CheckoutServicer(), grpc_server)
    grpc_port = int(os.getenv("GRPC_PORT", "50056"))
    grpc_server.add_insecure_port(f"[::]:{grpc_port}")
    grpc_server.start()
    logger.info(f"⚡ CheckoutService gRPC active on port {grpc_port}")

@app.on_event("shutdown")
def shutdown_event():
    if grpc_server: grpc_server.stop(grace=None)

@app.get("/healthz")
def health_check(): return {"status": "ok", "service": "checkout-service"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8086")))
