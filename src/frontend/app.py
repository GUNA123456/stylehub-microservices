"""
StyleHub - Storefront Web App Gateway
Python FastAPI Storefront communicating with backend microservices via native gRPC
"""

from fastapi import FastAPI, Request, Form, Response
from fastapi.responses import HTMLResponse, RedirectResponse
import os, sys, logging, grpc

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from genproto import stylehub_pb2, stylehub_pb2_grpc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Frontend")

app = FastAPI(title="StyleHub Storefront")

# gRPC Microservice Addresses
PRODUCT_CATALOG_GRPC = os.getenv("PRODUCT_CATALOG_GRPC_ADDR", "localhost:50051")
CART_GRPC = os.getenv("CART_GRPC_ADDR", "localhost:50052")
CURRENCY_GRPC = os.getenv("CURRENCY_GRPC_ADDR", "localhost:50053")
AD_GRPC = os.getenv("AD_GRPC_ADDR", "localhost:50057")
CHECKOUT_GRPC = os.getenv("CHECKOUT_GRPC_ADDR", "localhost:50056")

HTML_LAYOUT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{title} | StyleHub Storefront</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
        * {{ box-sizing: border-box; margin:0; padding:0; font-family: 'Inter', sans-serif; }}
        body {{ background: #f8fafc; color: #0f172a; min-height: 100vh; display: flex; flex-direction: column; }}
        header {{ background: #ffffff; border-bottom: 1px solid #e2e8f0; sticky: top; padding: 1rem 2rem; display: flex; justify-content: space-between; align-items: center; }}
        .logo {{ font-size: 1.5rem; font-weight: 800; color: #0f172a; text-decoration: none; }}
        .logo span {{ color: #ea580c; }}
        .nav {{ display: flex; align-items: center; gap: 1rem; }}
        .btn {{ background: #ea580c; color: white; border: none; padding: 0.6rem 1.2rem; border-radius: 0.5rem; font-weight: 700; text-decoration: none; cursor: pointer; }}
        .container {{ max-width: 1100px; margin: 2rem auto; padding: 0 1rem; flex: 1; }}
        .product-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 1.5rem; margin-top: 1.5rem; }}
        .card {{ background: white; border-radius: 0.75rem; padding: 1.25rem; border: 1px solid #e2e8f0; display: flex; flex-direction: column; justify-content: space-between; }}
        .ad-banner {{ background: #fff7ed; border: 1px solid #ffedd5; border-radius: 0.5rem; padding: 0.75rem 1rem; margin-bottom: 1.5rem; color: #c2410c; font-weight: 600; text-align: center; }}
    </style>
</head>
<body>
    <header>
        <a href="/" class="logo">🛍️ StyleHub<span>.</span></a>
        <div class="nav">
            <form action="/set-currency" method="post" style="margin:0;">
                <select name="currency_code" onchange="this.form.submit()" style="padding:0.4rem; border-radius:0.4rem; font-weight:600;">
                    <option value="USD" {usd_sel}>🇺🇸 USD</option>
                    <option value="EUR" {eur_sel}>🇪🇺 EUR</option>
                    <option value="GBP" {gbp_sel}>🇬🇧 GBP</option>
                    <option value="JPY" {jpy_sel}>🇯🇵 JPY</option>
                    <option value="CAD" {cad_sel}>🇨🇦 CAD</option>
                    <option value="INR" {inr_sel}>🇮🇳 INR</option>
                </select>
            </form>
            <a href="/cart" class="btn" style="background:#f1f5f9; color:#0f172a; border:1px solid #cbd5e1;">🛒 Cart ({cart_count})</a>
        </div>
    </header>
    <div class="container">
        {ad_banner}
        {content}
    </div>
</body>
</html>
"""

def _get_cart_count(user_id: str = "user-demo-123") -> int:
    try:
        stub = stylehub_pb2_grpc.CartServiceStub(grpc.insecure_channel(CART_GRPC))
        cart = stub.GetCart(stylehub_pb2.GetCartRequest(user_id=user_id), timeout=2)
        return sum(i.quantity for i in cart.items)
    except Exception: return 0

def _get_ads() -> str:
    try:
        stub = stylehub_pb2_grpc.AdServiceStub(grpc.insecure_channel(AD_GRPC))
        res = stub.GetAds(stylehub_pb2.AdRequest(context_keys=["clothing"]), timeout=2)
        if res.ads: return f'<div class="ad-banner">📢 {res.ads[0].text}</div>'
    except Exception: pass
    return ""

def _convert_price(units: int, nanos: int, to_code: str) -> str:
    if to_code == "USD": return f"${units}.00 USD"
    try:
        stub = stylehub_pb2_grpc.CurrencyServiceStub(grpc.insecure_channel(CURRENCY_GRPC))
        res = stub.Convert(stylehub_pb2.CurrencyConversionRequest(
            from_money=stylehub_pb2.Money(currency_code="USD", units=units, nanos=nanos),
            to_code=to_code
        ), timeout=2)
        return f"{res.units} {to_code}"
    except Exception: return f"${units}.00 USD"

@app.post("/set-currency")
def set_currency(currency_code: str = Form(...)):
    res = RedirectResponse(url="/", status_code=303)
    res.set_cookie(key="user_currency", value=currency_code)
    return res

@app.get("/", response_class=HTMLResponse)
def index_page(request: Request):
    user_currency = request.cookies.get("user_currency", "USD")
    cart_count = _get_cart_count()
    ad_html = _get_ads()

    try:
        stub = stylehub_pb2_grpc.ProductCatalogServiceStub(grpc.insecure_channel(PRODUCT_CATALOG_GRPC))
        response = stub.ListProducts(stylehub_pb2.Empty(), timeout=2)
        products = response.products
    except Exception as e:
        content = f'<h2 style="color:#ef4444;">Product Catalog Unreachable via gRPC ({PRODUCT_CATALOG_GRPC})</h2><p>{e}</p>'
        return HTML_LAYOUT.format(title="Error", content=content, ad_banner="", cart_count=cart_count, usd_sel="", eur_sel="", gbp_sel="", jpy_sel="", cad_sel="", inr_sel="")

    cards = ""
    for p in products:
        price_str = _convert_price(p.price_usd.units, p.price_usd.nanos, user_currency)
        cards += f"""
        <div class="card">
            <div>
                <span style="font-size:0.75rem; font-weight:700; background:#e2e8f0; padding:0.2rem 0.4rem; border-radius:0.2rem;">{p.categories[0].upper()}</span>
                <h3 style="margin-top:0.5rem; font-size:1.1rem; font-weight:700;">{p.name}</h3>
                <p style="color:#64748b; font-size:0.85rem; margin-top:0.4rem;">{p.description}</p>
            </div>
            <div style="margin-top:1.25rem;">
                <div style="font-size:1.2rem; font-weight:800; color:#ea580c;">{price_str}</div>
                <form action="/add-to-cart" method="post" style="margin-top:0.75rem;">
                    <input type="hidden" name="product_id" value="{p.id}">
                    <button type="submit" class="btn" style="width:100%;">Add to Cart</button>
                </form>
            </div>
        </div>
        """

    content = f"""
    <h1 style="font-size:2rem; font-weight:800;">Featured Collection (gRPC Microservices Mesh)</h1>
    <div class="product-grid">{cards}</div>
    """

    return HTML_LAYOUT.format(
        title="Storefront", ad_banner=ad_html, content=content, cart_count=cart_count,
        usd_sel="selected" if user_currency=="USD" else "",
        eur_sel="selected" if user_currency=="EUR" else "",
        gbp_sel="selected" if user_currency=="GBP" else "",
        jpy_sel="selected" if user_currency=="JPY" else "",
        cad_sel="selected" if user_currency=="CAD" else "",
        inr_sel="selected" if user_currency=="INR" else ""
    )

@app.post("/add-to-cart")
def add_to_cart(product_id: str = Form(...), user_id: str = "user-demo-123"):
    try:
        stub = stylehub_pb2_grpc.CartServiceStub(grpc.insecure_channel(CART_GRPC))
        stub.AddItem(stylehub_pb2.AddItemRequest(user_id=user_id, item=stylehub_pb2.CartItem(product_id=product_id, quantity=1)), timeout=2)
    except Exception as e:
        logger.error(f"gRPC Cart AddItem error: {e}")
    return RedirectResponse(url="/cart", status_code=303)

@app.get("/cart", response_class=HTMLResponse)
def view_cart(request: Request, user_id: str = "user-demo-123"):
    user_currency = request.cookies.get("user_currency", "USD")
    cart_count = _get_cart_count(user_id)

    items = []
    try:
        stub = stylehub_pb2_grpc.CartServiceStub(grpc.insecure_channel(CART_GRPC))
        cart = stub.GetCart(stylehub_pb2.GetCartRequest(user_id=user_id), timeout=2)
        items = cart.items
    except Exception: pass

    if not items:
        content = '<div style="text-align:center; padding:3rem;"><h2>🛒 Your Cart is Empty</h2><a href="/" class="btn" style="display:inline-block; margin-top:1rem;">Shop Collection</a></div>'
    else:
        rows, total_usd = "", 0
        pc_stub = stylehub_pb2_grpc.ProductCatalogServiceStub(grpc.insecure_channel(PRODUCT_CATALOG_GRPC))
        for item in items:
            p_name, price_u = item.product_id, 50
            try:
                p = pc_stub.GetProduct(stylehub_pb2.GetProductRequest(id=item.product_id), timeout=2)
                p_name, price_u = p.name, p.price_usd.units
            except Exception: pass
            sub = price_u * item.quantity
            total_usd += sub
            rows += f'<tr style="border-bottom:1px solid #e2e8f0;"><td style="padding:0.75rem;">{p_name}</td><td style="padding:0.75rem;">${price_u}.00</td><td style="padding:0.75rem;">{item.quantity}</td><td style="padding:0.75rem; font-weight:700; color:#ea580c;">${sub}.00</td></tr>'

        formatted_total = _convert_price(total_usd, 0, user_currency)
        content = f"""
        <h1 style="font-size:1.8rem; font-weight:800; margin-bottom:1rem;">Shopping Cart</h1>
        <table style="width:100%; background:white; border-radius:0.5rem; padding:1rem; border-collapse:collapse;">
            <thead><tr style="border-bottom:2px solid #e2e8f0; text-align:left;"><th>Product</th><th>Price</th><th>Qty</th><th>Subtotal</th></tr></thead>
            <tbody>{rows}</tbody>
        </table>
        <div style="display:flex; justify-content:space-between; align-items:center; margin-top:1.5rem;">
            <h3>Total: <span style="color:#ea580c;">{formatted_total}</span></h3>
            <form action="/checkout" method="post"><button type="submit" class="btn">Proceed to Checkout</button></form>
        </div>
        """

    return HTML_LAYOUT.format(title="Cart", ad_banner="", content=content, cart_count=cart_count, usd_sel="", eur_sel="", gbp_sel="", jpy_sel="", cad_sel="", inr_sel="")

@app.post("/checkout", response_class=HTMLResponse)
def checkout(request: Request, user_id: str = "user-demo-123"):
    user_currency = request.cookies.get("user_currency", "USD")
    order_id, tracking_id = "ORD-SH-SUCCESS", "SH-TRK-98765"
    try:
        stub = stylehub_pb2_grpc.CheckoutServiceStub(grpc.insecure_channel(CHECKOUT_GRPC))
        res = stub.PlaceOrder(stylehub_pb2.PlaceOrderRequest(
            user_id=user_id,
            user_currency=user_currency,
            email="customer@stylehub.com",
            address=stylehub_pb2.Address(street_address="123 Fashion Ave", city="New York", state="NY", country="USA", zip_code=10001),
            credit_card=stylehub_pb2.CreditCardInfo(credit_card_number="4532-1234-5678-9012", credit_card_cvv=123, credit_card_expiration_year=2028, credit_card_expiration_month=12)
        ), timeout=5)
        order_id = res.order.order_id
        tracking_id = res.order.shipping_tracking_id
    except Exception as e:
        logger.error(f"gRPC Checkout error: {e}")

    content = f"""
    <div style="background:#f0fdf4; border:1px solid #bbf7d0; border-radius:0.75rem; padding:2rem; text-align:center; max-width:500px; margin:2rem auto;">
        <h2>🎉 Order Placed Successfully via gRPC!</h2>
        <p style="margin-top:0.5rem;">Order ID: <strong>{order_id}</strong></p>
        <p>Carrier Tracking ID: <strong>{tracking_id}</strong></p>
        <a href="/" class="btn" style="display:inline-block; margin-top:1.5rem;">Continue Shopping</a>
    </div>
    """
    return HTML_LAYOUT.format(title="Order Complete", ad_banner="", content=content, cart_count=0, usd_sel="", eur_sel="", gbp_sel="", jpy_sel="", cad_sel="", inr_sel="")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
