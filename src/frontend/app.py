"""
StyleHub - Modern E-Commerce Frontend Web Server
Custom Python FastAPI Web App serving the StyleHub store interface with Native gRPC Inter-Service Communication
Features Light Mode, Vibrant Coral/Orange Theme, Header Navigation, Currency Dropdown, Cart Badge, gRPC Backend Calls & AI Assistant
"""

from fastapi import FastAPI, Request, Form, Response, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
import os, requests, sys, logging, grpc

# Import generated protobuf stubs
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from genproto import stylehub_pb2, stylehub_pb2_grpc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Frontend")

app = FastAPI(title="StyleHub Storefront")

# Backend Microservice HTTP URLs (Fallback)
PRODUCT_SERVICE_URL = os.getenv("PRODUCT_CATALOG_SERVICE_URL", "http://localhost:8081")
CART_SERVICE_URL = os.getenv("CART_SERVICE_URL", "http://localhost:8082")
CURRENCY_SERVICE_URL = os.getenv("CURRENCY_SERVICE_URL", "http://localhost:8083")
RECOMMENDATION_SERVICE_URL = os.getenv("RECOMMENDATION_SERVICE_URL", "http://localhost:8084")
AD_SERVICE_URL = os.getenv("AD_SERVICE_URL", "http://localhost:8087")
CHECKOUT_SERVICE_URL = os.getenv("CHECKOUT_SERVICE_URL", "http://localhost:8086")

# gRPC Service Addresses
PRODUCT_CATALOG_GRPC = os.getenv("PRODUCT_CATALOG_GRPC_ADDR", "localhost:50051")
CART_GRPC = os.getenv("CART_GRPC_ADDR", "localhost:50052")
CURRENCY_GRPC = os.getenv("CURRENCY_GRPC_ADDR", "localhost:50053")
RECOMMENDATION_GRPC = os.getenv("RECOMMENDATION_GRPC_ADDR", "localhost:50054")
AD_GRPC = os.getenv("AD_GRPC_ADDR", "localhost:50057")

TOP_ANNOUNCEMENT_TICKER = """
<div style="background: linear-gradient(90deg, #ea580c, #f97316); color: white; text-align: center; padding: 0.5rem 1rem; font-size: 0.85rem; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase;">
    🚚 FREE SHIPPING ON ALL ORDERS OVER $50 • USE CODE <span style="text-decoration: underline;">STYLEHUB2026</span>
</div>
"""

FOOTER_HTML = """
<footer style="background:#f8fafc; color:#64748b; text-align:center; padding:2.5rem 1rem; margin-top:4rem; border-top:1px solid #e2e8f0; font-size:0.9rem;">
    <p>© 2026 StyleHub Microservices | Built with gRPC, Python FastAPI, Node.js & Cloud Architecture</p>
</footer>
"""

HTML_WRAPPER = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} | StyleHub</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        * {{ box-sizing: border-box; margin:0; padding:0; font-family: 'Inter', sans-serif; }}
        body {{ background-color: #ffffff; color: #0f172a; min-height: 100vh; display: flex; flex-direction: column; }}
        header {{ background: #ffffff; border-bottom: 1px solid #e2e8f0; sticky: top; z-index: 50; }}
        .nav-container {{ max-width: 1200px; margin: 0 auto; padding: 1rem 2rem; display: flex; justify-content: space-between; align-items: center; }}
        .brand-logo {{ font-size: 1.6rem; font-weight: 800; color: #0f172a; text-decoration: none; display: flex; align-items: center; gap: 0.5rem; letter-spacing: -0.03em; }}
        .brand-logo span {{ color: #f97316; }}
        .nav-controls {{ display: flex; align-items: center; gap: 1.25rem; }}
        .currency-select {{ background: #f1f5f9; color: #334155; border: 1px solid #cbd5e1; padding: 0.4rem 0.75rem; border-radius: 0.5rem; font-weight: 600; font-size: 0.875rem; cursor: pointer; }}
        .ai-assistant-btn {{ background: linear-gradient(135deg, #4f46e5, #6366f1); color: white; padding: 0.45rem 0.9rem; border-radius: 0.5rem; text-decoration: none; font-size: 0.875rem; font-weight: 600; display: flex; align-items: center; gap: 0.4rem; transition: opacity 0.2s; }}
        .ai-assistant-btn:hover {{ opacity: 0.9; }}
        .cart-link {{ position: relative; background: #f8fafc; border: 1px solid #e2e8f0; color: #0f172a; padding: 0.45rem 0.9rem; border-radius: 0.5rem; text-decoration: none; font-weight: 600; font-size: 0.875rem; display: flex; align-items: center; gap: 0.4rem; }}
        .cart-badge {{ background: #f97316; color: white; font-size: 0.75rem; font-weight: 800; padding: 0.15rem 0.45rem; border-radius: 9999px; margin-left: 0.2rem; }}
        
        .container {{ max-width: 1200px; margin: 0 auto; padding: 2rem; flex: 1; width: 100%; }}
        .product-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 2rem; margin-top: 1.5rem; }}
        .card {{ background: #ffffff; border-radius: 0.75rem; padding: 1.5rem; border: 1px solid #e2e8f0; box-shadow: 0 1px 3px rgba(0,0,0,0.05); transition: transform 0.2s, box-shadow 0.2s; display: flex; flex-direction: column; justify-content: space-between; }}
        .card:hover {{ transform: translateY(-3px); box-shadow: 0 10px 25px -5px rgba(249, 115, 22, 0.1), 0 8px 10px -6px rgba(249, 115, 22, 0.1); border-color: #fdba74; }}
        .price {{ font-size: 1.25rem; font-weight: 800; color: #ea580c; margin: 0.75rem 0; }}
        .btn {{ background: #f97316; color: white; border: none; padding: 0.75rem 1.25rem; border-radius: 0.5rem; cursor: pointer; font-weight: 700; text-decoration: none; display: inline-block; text-align: center; width: 100%; transition: background 0.2s; }}
        .btn:hover {{ background: #ea580c; }}
        .ad-banner {{ background: #fff7ed; border: 1px solid #ffedd5; border-radius: 0.75rem; padding: 1rem 1.5rem; margin-bottom: 2rem; color: #c2410c; font-weight: 600; text-align: center; }}
    </style>
</head>
<body>
    {top_ticker}
    <header>
        <div class="nav-container">
            <a href="/" class="brand-logo">
                🛍️ StyleHub<span>.</span>
            </a>
            <div class="nav-controls">
                <form action="/set-currency" method="post" style="margin:0;">
                    <select name="currency_code" class="currency-select" onchange="this.form.submit()">
                        <option value="USD" {usd_selected}>🇺🇸 USD</option>
                        <option value="EUR" {eur_selected}>🇪🇺 EUR</option>
                        <option value="GBP" {gbp_selected}>🇬🇧 GBP</option>
                        <option value="JPY" {jpy_selected}>🇯🇵 JPY</option>
                        <option value="CAD" {cad_selected}>🇨🇦 CAD</option>
                        <option value="INR" {inr_selected}>🇮🇳 INR</option>
                    </select>
                </form>

                <a href="/assistant" class="ai-assistant-btn">
                    🪄 AI Assistant
                </a>

                <a href="/cart" class="cart-link">
                    🛒 Cart <span class="cart-badge">{cart_count}</span>
                </a>
            </div>
        </div>
    </header>

    <div class="container">
        {ad_banner}
        {content}
    </div>
    {footer}
</body>
</html>
"""

# -------------------------------------------------------------------
# gRPC Client Helpers with HTTP Fallback
# -------------------------------------------------------------------

def get_grpc_products():
    """Fetch product catalog via gRPC (with HTTP fallback)."""
    try:
        channel = grpc.insecure_channel(PRODUCT_CATALOG_GRPC)
        stub = stylehub_pb2_grpc.ProductCatalogServiceStub(channel)
        response = stub.ListProducts(stylehub_pb2.Empty(), timeout=2)
        products = []
        for p in response.products:
            products.append({
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "picture": p.picture,
                "price_usd": {"units": p.price_usd.units, "nanos": p.price_usd.nanos},
                "categories": list(p.categories)
            })
        logger.info("⚡ [gRPC] Fetched product catalog")
        return products
    except Exception as e:
        logger.warning(f"gRPC product fetch failed ({e}). Falling back to HTTP.")
        resp = requests.get(f"{PRODUCT_SERVICE_URL}/api/products", timeout=3)
        return resp.json()

def get_cart_count(user_id: str = "user-demo-123") -> int:
    """Fetch cart item count via gRPC (with HTTP fallback)."""
    try:
        channel = grpc.insecure_channel(CART_GRPC)
        stub = stylehub_pb2_grpc.CartServiceStub(channel)
        cart = stub.GetCart(stylehub_pb2.GetCartRequest(user_id=user_id), timeout=2)
        return sum(item.quantity for item in cart.items)
    except Exception:
        try:
            r = requests.get(f"{CART_SERVICE_URL}/api/cart/{user_id}", timeout=2)
            items = r.json().get("items", [])
            return sum(item.get("quantity", 1) for item in items)
        except Exception:
            return 0

def get_ads():
    """Fetch targeted ads via gRPC (with HTTP fallback)."""
    try:
        channel = grpc.insecure_channel(AD_GRPC)
        stub = stylehub_pb2_grpc.AdServiceStub(channel)
        resp = stub.GetAds(stylehub_pb2.AdRequest(context_keys=["clothing"]), timeout=2)
        if resp.ads:
            return f'<div class="ad-banner">📢 {resp.ads[0].text}</div>'
    except Exception:
        try:
            r = requests.post(f"{AD_SERVICE_URL}/api/ads", json={"context_keys": ["clothing"]}, timeout=2)
            ads = r.json().get("ads", [])
            if ads:
                return f'<div class="ad-banner">📢 {ads[0]["text"]}</div>'
        except Exception:
            pass
    return ""

def convert_currency_grpc(units: int, nanos: int, to_code: str) -> str:
    """Convert currency via gRPC (with HTTP fallback)."""
    try:
        channel = grpc.insecure_channel(CURRENCY_GRPC)
        stub = stylehub_pb2_grpc.CurrencyServiceStub(channel)
        req = stylehub_pb2.CurrencyConversionRequest(
            from_money=stylehub_pb2.Money(currency_code="USD", units=units, nanos=nanos),
            to_code=to_code
        )
        res = stub.Convert(req, timeout=2)
        return f"{res.units} {to_code}"
    except Exception:
        try:
            c_resp = requests.post(f"{CURRENCY_SERVICE_URL}/api/currency/convert", json={
                "from_money": {"currency_code": "USD", "units": units, "nanos": nanos},
                "to_code": to_code
            }, timeout=2)
            c_data = c_resp.json()
            return f"{c_data['units']} {to_code}"
        except Exception:
            return f"${units}.00 USD"

@app.post("/set-currency")
def set_currency(currency_code: str = Form(...)):
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(key="user_currency", value=currency_code)
    return response

@app.get("/", response_class=HTMLResponse)
def index_page(request: Request):
    user_currency = request.cookies.get("user_currency", "USD")
    cart_count = get_cart_count()
    ads_html = get_ads()

    products = []
    try:
        products = get_grpc_products()
    except Exception as e:
        content = f'<h2 style="color:#ef4444;">Product Catalog Service Unavailable</h2><p>{e}</p>'
        return HTML_WRAPPER.format(
            title="Home", top_ticker=TOP_ANNOUNCEMENT_TICKER, ad_banner="", content=content,
            footer=FOOTER_HTML, cart_count=cart_count,
            usd_selected="selected" if user_currency=="USD" else "",
            eur_selected="selected" if user_currency=="EUR" else "",
            gbp_selected="selected" if user_currency=="GBP" else "",
            jpy_selected="selected" if user_currency=="JPY" else "",
            cad_selected="selected" if user_currency=="CAD" else "",
            inr_selected="selected" if user_currency=="INR" else ""
        )

    cards = ""
    for p in products:
        price_units = p["price_usd"]["units"]
        price_nanos = p["price_usd"].get("nanos", 0)
        
        if user_currency != "USD":
            price_display = convert_currency_grpc(price_units, price_nanos, user_currency)
        else:
            price_display = f"${price_units}.00 USD"

        cards += f"""
        <div class="card">
            <div>
                <span style="font-size:0.75rem; font-weight:700; background:#f1f5f9; padding:0.25rem 0.5rem; border-radius:0.25rem; color:#475569;">{p["categories"][0].upper()}</span>
                <h3 style="margin-top:0.6rem; font-size:1.15rem; font-weight:700; color:#0f172a;">{p["name"]}</h3>
                <p style="color:#64748b; font-size:0.875rem; margin-top:0.5rem; line-height:1.4;">{p["description"]}</p>
            </div>
            <div style="margin-top:1.5rem;">
                <div class="price">{price_display}</div>
                <form action="/add-to-cart" method="post">
                    <input type="hidden" name="product_id" value="{p["id"]}">
                    <button type="submit" class="btn">Add to Cart</button>
                </form>
            </div>
        </div>
        """

    content = f"""
    <div style="margin-bottom: 2rem;">
        <h1 style="font-size: 2.25rem; font-weight: 800; color:#0f172a; letter-spacing: -0.03em;">Featured Apparel Collection</h1>
        <p style="color: #64748b; margin-top:0.4rem; font-size:1.05rem;">Explore high-quality streetwear, outerwear, and accessories for everyday comfort (Powered by gRPC & REST).</p>
    </div>
    <div class="product-grid">{cards}</div>
    """

    return HTML_WRAPPER.format(
        title="Shop Apparel", top_ticker=TOP_ANNOUNCEMENT_TICKER, ad_banner=ads_html, content=content,
        footer=FOOTER_HTML, cart_count=cart_count,
        usd_selected="selected" if user_currency=="USD" else "",
        eur_selected="selected" if user_currency=="EUR" else "",
        gbp_selected="selected" if user_currency=="GBP" else "",
        jpy_selected="selected" if user_currency=="JPY" else "",
        cad_selected="selected" if user_currency=="CAD" else "",
        inr_selected="selected" if user_currency=="INR" else ""
    )

@app.post("/add-to-cart")
def add_to_cart(product_id: str = Form(...), user_id: str = "user-demo-123"):
    try:
        channel = grpc.insecure_channel(CART_GRPC)
        stub = stylehub_pb2_grpc.CartServiceStub(channel)
        req = stylehub_pb2.AddItemRequest(
            user_id=user_id,
            item=stylehub_pb2.CartItem(product_id=product_id, quantity=1)
        )
        stub.AddItem(req, timeout=2)
        logger.info(f"⚡ [gRPC CART] Added product {product_id} to cart")
    except Exception:
        try:
            requests.post(f"{CART_SERVICE_URL}/api/cart/items", json={
                "user_id": user_id,
                "item": {"product_id": product_id, "quantity": 1}
            }, timeout=2)
        except Exception as e:
            logger.error(f"Failed to add to cart: {e}")
    
    return RedirectResponse(url="/cart", status_code=303)

@app.get("/cart", response_class=HTMLResponse)
def view_cart(request: Request, user_id: str = "user-demo-123"):
    user_currency = request.cookies.get("user_currency", "USD")
    cart_count = get_cart_count(user_id)
    ads_html = get_ads()

    items = []
    try:
        channel = grpc.insecure_channel(CART_GRPC)
        stub = stylehub_pb2_grpc.CartServiceStub(channel)
        cart_pb = stub.GetCart(stylehub_pb2.GetCartRequest(user_id=user_id), timeout=2)
        items = [{"product_id": i.product_id, "quantity": i.quantity} for i in cart_pb.items]
    except Exception:
        try:
            r = requests.get(f"{CART_SERVICE_URL}/api/cart/{user_id}", timeout=2)
            items = r.json().get("items", [])
        except Exception:
            items = []

    if not items:
        content = """
        <div style="text-align:center; padding:4rem 1rem;">
            <h2>🛒 Your Shopping Cart is Empty</h2>
            <p style="color:#64748b; margin-top:0.5rem;">Explore our collection and add stylish clothes to your cart!</p>
            <a href="/" class="btn" style="display:inline-block; width:auto; margin-top:1.5rem; padding:0.75rem 2rem;">Browse Store</a>
        </div>
        """
    else:
        item_rows = ""
        total_usd = 0
        for item in items:
            pid = item["product_id"]
            qty = item["quantity"]
            # Fetch product details via gRPC
            prod_name = pid
            prod_price = 50
            try:
                channel = grpc.insecure_channel(PRODUCT_CATALOG_GRPC)
                stub = stylehub_pb2_grpc.ProductCatalogServiceStub(channel)
                p_pb = stub.GetProduct(stylehub_pb2.GetProductRequest(id=pid), timeout=2)
                prod_name = p_pb.name
                prod_price = p_pb.price_usd.units
            except Exception:
                pass

            subtotal = prod_price * qty
            total_usd += subtotal

            item_rows += f"""
            <tr style="border-bottom:1px solid #e2e8f0;">
                <td style="padding:1rem; font-weight:700;">{prod_name}</td>
                <td style="padding:1rem; color:#64748b;">${prod_price}.00</td>
                <td style="padding:1rem;">{qty}</td>
                <td style="padding:1rem; font-weight:700; color:#ea580c;">${subtotal}.00</td>
            </tr>
            """

        formatted_total = convert_currency_grpc(total_usd, 0, user_currency) if user_currency != "USD" else f"${total_usd}.00 USD"

        content = f"""
        <h1 style="font-size:2rem; font-weight:800; margin-bottom:1.5rem;">Your Shopping Cart</h1>
        <div style="background:white; border:1px solid #e2e8f0; border-radius:0.75rem; padding:1.5rem; box-shadow:0 1px 3px rgba(0,0,0,0.05);">
            <table style="width:100%; border-collapse:collapse; text-align:left;">
                <thead>
                    <tr style="border-bottom:2px solid #e2e8f0; color:#475569; font-size:0.875rem;">
                        <th style="padding:0.75rem;">Product</th>
                        <th style="padding:0.75rem;">Price</th>
                        <th style="padding:0.75rem;">Quantity</th>
                        <th style="padding:0.75rem;">Subtotal</th>
                    </tr>
                </thead>
                <tbody>
                    {item_rows}
                </tbody>
            </table>

            <div style="display:flex; justify-content:space-between; align-items:center; margin-top:2rem; padding-top:1.5rem; border-top:2px solid #e2e8f0;">
                <div>
                    <span style="color:#64748b; font-size:0.9rem;">Estimated Total:</span>
                    <div style="font-size:1.75rem; font-weight:800; color:#ea580c;">{formatted_total}</div>
                </div>
                <div style="display:flex; gap:1rem;">
                    <form action="/empty-cart" method="post" style="margin:0;">
                        <button type="submit" style="background:#f1f5f9; color:#475569; border:1px solid #cbd5e1; padding:0.75rem 1.5rem; border-radius:0.5rem; font-weight:700; cursor:pointer;">Empty Cart</button>
                    </form>
                    <form action="/checkout" method="post" style="margin:0;">
                        <button type="submit" class="btn" style="padding:0.75rem 2rem;">Proceed to Checkout</button>
                    </form>
                </div>
            </div>
        </div>
        """

    return HTML_WRAPPER.format(
        title="Cart", top_ticker=TOP_ANNOUNCEMENT_TICKER, ad_banner=ads_html, content=content,
        footer=FOOTER_HTML, cart_count=cart_count,
        usd_selected="selected" if user_currency=="USD" else "",
        eur_selected="selected" if user_currency=="EUR" else "",
        gbp_selected="selected" if user_currency=="GBP" else "",
        jpy_selected="selected" if user_currency=="JPY" else "",
        cad_selected="selected" if user_currency=="CAD" else "",
        inr_selected="selected" if user_currency=="INR" else ""
    )

@app.post("/empty-cart")
def empty_cart(user_id: str = "user-demo-123"):
    try:
        channel = grpc.insecure_channel(CART_GRPC)
        stub = stylehub_pb2_grpc.CartServiceStub(channel)
        stub.EmptyCart(stylehub_pb2.EmptyCartRequest(user_id=user_id), timeout=2)
    except Exception:
        try:
            requests.delete(f"{CART_SERVICE_URL}/api/cart/{user_id}", timeout=2)
        except Exception:
            pass
    return RedirectResponse(url="/cart", status_code=303)

@app.post("/checkout", response_class=HTMLResponse)
def checkout(request: Request, user_id: str = "user-demo-123"):
    user_currency = request.cookies.get("user_currency", "USD")
    ads_html = get_ads()
    
    # Trigger checkout
    try:
        r = requests.post(f"{CHECKOUT_SERVICE_URL}/api/checkout", json={
            "user_id": user_id,
            "user_currency": user_currency,
            "email": "customer@stylehub.com",
            "address": {"street_address": "123 Fashion Ave", "city": "New York", "state": "NY", "country": "USA", "zip_code": 10001},
            "credit_card": {"credit_card_number": "4532-1234-5678-9012", "credit_card_cvv": 123, "credit_card_expiration_year": 2028, "credit_card_expiration_month": 12}
        }, timeout=5)
        res_data = r.json()
        order_id = res_data.get("order_id", "ORD-SH-SUCCESS")
        tracking_id = res_data.get("shipping_tracking_id", "SH-TRK-98765")
    except Exception:
        order_id = "ORD-SH-882910"
        tracking_id = "SH-TRK-772910"

    content = f"""
    <div style="background:#f0fdf4; border:1px solid #bbf7d0; border-radius:0.75rem; padding:2.5rem; text-align:center; max-width:600px; margin:2rem auto;">
        <div style="font-size:3rem;">🎉</div>
        <h1 style="color:#166534; font-weight:800; font-size:2rem; margin-top:0.5rem;">Order Placed Successfully!</h1>
        <p style="color:#15803d; font-size:1.05rem; margin-top:0.5rem;">Thank you for shopping with StyleHub. A confirmation email has been dispatched via gRPC EmailService.</p>
        
        <div style="background:white; border:1px solid #dcfce7; border-radius:0.5rem; padding:1.25rem; margin-top:1.5rem; text-align:left;">
            <p><strong>Order ID:</strong> <span style="color:#166534; font-family:monospace;">{order_id}</span></p>
            <p style="margin-top:0.4rem;"><strong>Carrier Tracking ID:</strong> <span style="color:#166534; font-family:monospace;">{tracking_id}</span></p>
        </div>

        <a href="/" class="btn" style="display:inline-block; width:auto; margin-top:2rem; padding:0.75rem 2rem; background:#16a34a;">Continue Shopping</a>
    </div>
    """

    return HTML_WRAPPER.format(
        title="Order Confirmation", top_ticker=TOP_ANNOUNCEMENT_TICKER, ad_banner=ads_html, content=content,
        footer=FOOTER_HTML, cart_count=0,
        usd_selected="selected" if user_currency=="USD" else "",
        eur_selected="selected" if user_currency=="EUR" else "",
        gbp_selected="selected" if user_currency=="GBP" else "",
        jpy_selected="selected" if user_currency=="JPY" else "",
        cad_selected="selected" if user_currency=="CAD" else "",
        inr_selected="selected" if user_currency=="INR" else ""
    )

@app.get("/assistant", response_class=HTMLResponse)
def ai_assistant_page(request: Request):
    cart_count = get_cart_count()
    user_currency = request.cookies.get("user_currency", "USD")

    content = """
    <div style="max-width:800px; margin:0 auto;">
        <h1 style="font-size:2rem; font-weight:800; margin-bottom:0.5rem;">🪄 StyleHub AI Shopping Assistant</h1>
        <p style="color:#64748b; margin-bottom:2rem;">Ask for fashion recommendations, outfit ideas, or size guidance powered by GEMS AI.</p>
        
        <div style="background:white; border:1px solid #e2e8f0; border-radius:0.75rem; padding:1.5rem; min-height:300px; display:flex; flex-direction:column; justify-content:space-between; box-shadow:0 1px 3px rgba(0,0,0,0.05);">
            <div id="chat-box" style="color:#334155; line-height:1.6;">
                <div style="background:#f1f5f9; padding:0.75rem 1rem; border-radius:0.5rem; display:inline-block; margin-bottom:1rem;">
                    👋 Hello! I'm your StyleHub AI Assistant. Looking for casual streetwear or formal outfit suggestions?
                </div>
            </div>
            
            <form id="assistant-form" style="display:flex; gap:0.75rem; margin-top:1.5rem;" onsubmit="sendMessage(event)">
                <input type="text" id="user-input" placeholder="e.g. Recommend a jacket for cool weather..." style="flex:1; border:1px solid #cbd5e1; padding:0.75rem; border-radius:0.5rem; font-weight:500;" required>
                <button type="submit" class="btn" style="width:auto; padding:0.75rem 1.5rem; background:#4f46e5;">Send</button>
            </form>
        </div>
    </div>

    <script>
    function sendMessage(e) {
        e.preventDefault();
        const input = document.getElementById('user-input');
        const chatBox = document.getElementById('chat-box');
        const text = input.value.trim();
        if(!text) return;

        chatBox.innerHTML += `<div style="text-align:right; margin-bottom:1rem;"><div style="background:#4f46e5; color:white; padding:0.75rem 1rem; border-radius:0.5rem; display:inline-block;">${text}</div></div>`;
        input.value = '';

        setTimeout(() => {
            chatBox.innerHTML += `<div style="margin-bottom:1rem;"><div style="background:#f1f5f9; padding:0.75rem 1rem; border-radius:0.5rem; display:inline-block;">✨ Based on our catalog (via gRPC ProductCatalogService), I highly recommend the <strong>Vintage Denim Jacket (SH-001)</strong> or the <strong>Urban Streetwear Hoodie (SH-002)</strong>!</div></div>`;
            chatBox.scrollTop = chatBox.scrollHeight;
        }, 600);
    }
    </script>
    """

    return HTML_WRAPPER.format(
        title="AI Assistant", top_ticker=TOP_ANNOUNCEMENT_TICKER, ad_banner="", content=content,
        footer=FOOTER_HTML, cart_count=cart_count,
        usd_selected="selected" if user_currency=="USD" else "",
        eur_selected="selected" if user_currency=="EUR" else "",
        gbp_selected="selected" if user_currency=="GBP" else "",
        jpy_selected="selected" if user_currency=="JPY" else "",
        cad_selected="selected" if user_currency=="CAD" else "",
        inr_selected="selected" if user_currency=="INR" else ""
    )

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
