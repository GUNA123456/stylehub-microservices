"""
StyleHub - Modern E-Commerce Frontend Web Server
Custom Python FastAPI Web App serving the StyleHub store interface
Features Light Mode, Vibrant Coral/Orange Theme, Header Navigation, Currency Dropdown, Cart Badge & AI Assistant
"""

from fastapi import FastAPI, Request, Form, Response, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
import os, requests

app = FastAPI(title="StyleHub Storefront")

# Backend Microservice URLs
PRODUCT_SERVICE_URL = os.getenv("PRODUCT_CATALOG_SERVICE_URL", "http://localhost:8081")
CART_SERVICE_URL = os.getenv("CART_SERVICE_URL", "http://localhost:8082")
CURRENCY_SERVICE_URL = os.getenv("CURRENCY_SERVICE_URL", "http://localhost:8083")
RECOMMENDATION_SERVICE_URL = os.getenv("RECOMMENDATION_SERVICE_URL", "http://localhost:8084")
AD_SERVICE_URL = os.getenv("AD_SERVICE_URL", "http://localhost:8085")
CHECKOUT_SERVICE_URL = os.getenv("CHECKOUT_SERVICE_URL", "http://localhost:8089")

TOP_ANNOUNCEMENT_TICKER = """
<div style="background: linear-gradient(90deg, #ea580c, #f97316); color: white; text-align: center; padding: 0.5rem 1rem; font-size: 0.85rem; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase;">
    🚚 FREE SHIPPING ON ALL ORDERS OVER $50 • USE CODE <span style="text-decoration: underline;">STYLEHUB2026</span>
</div>
"""

FOOTER_HTML = """
<footer style="background:#f8fafc; color:#64748b; text-align:center; padding:2.5rem 1rem; margin-top:4rem; border-top:1px solid #e2e8f0; font-size:0.9rem;">
    <p>© 2026 StyleHub Microservices | Built with Python FastAPI, Node.js & Cloud Architecture</p>
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

def get_cart_count(user_id: str = "user-demo-123") -> int:
    try:
        r = requests.get(f"{CART_SERVICE_URL}/api/cart/{user_id}", timeout=2)
        items = r.json().get("items", [])
        return sum(item.get("quantity", 1) for item in items)
    except Exception:
        return 0

def get_ads():
    try:
        r = requests.post(f"{AD_SERVICE_URL}/api/ads", json={"context_keys": ["clothing"]}, timeout=2)
        ads = r.json().get("ads", [])
        if ads:
            return f'<div class="ad-banner">📢 {ads[0]["text"]}</div>'
    except Exception:
        pass
    return ""

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

    # Fetch Products
    products = []
    try:
        r = requests.get(f"{PRODUCT_SERVICE_URL}/api/products", timeout=3)
        products = r.json()
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
        price_usd = p["price_usd"]["units"]
        price_display = f"${price_usd}.00 USD"
        
        # Convert currency if not USD
        if user_currency != "USD":
            try:
                c_resp = requests.post(f"{CURRENCY_SERVICE_URL}/api/currency/convert", json={
                    "from_money": {"currency_code": "USD", "units": price_usd, "nanos": 0},
                    "to_code": user_currency
                }, timeout=2)
                c_data = c_resp.json()
                price_display = f"{c_data['units']} {user_currency}"
            except Exception:
                pass

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
        <p style="color: #64748b; margin-top:0.4rem; font-size:1.05rem;">Explore high-quality streetwear, outerwear, and accessories for everyday comfort.</p>
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

@app.get("/assistant", response_class=HTMLResponse)
def assistant_page(request: Request):
    user_currency = request.cookies.get("user_currency", "USD")
    cart_count = get_cart_count()

    content = """
    <div style="background:#ffffff; padding:2.5rem; border-radius:1rem; border:1px solid #e2e8f0; max-width:700px; margin:2rem auto; box-shadow:0 4px 6px -1px rgba(0,0,0,0.05);">
        <div style="display:flex; align-items:center; gap:0.75rem; margin-bottom:1rem;">
            <span style="font-size:2rem;">🪄</span>
            <h1 style="font-size:1.75rem; font-weight:800; color:#0f172a;">AI Shopping Assistant</h1>
        </div>
        <p style="color:#64748b; margin-bottom:1.5rem; line-height:1.5;">Ask our AI assistant for outfit suggestions, sizing guides, or personalized style recommendations.</p>
        
        <div style="background:#f8fafc; padding:1.25rem; border-radius:0.75rem; border:1px solid #e2e8f0; margin-bottom:1.5rem;">
            <p style="font-weight:600; color:#334155;">🤖 Assistant:</p>
            <p style="color:#475569; margin-top:0.5rem;">"Hello! I recommend pairing the <strong>Urban Streetwear Hoodie</strong> with our <strong>Tailored Slim-Fit Chinos</strong> for a modern, relaxed weekend look!"</p>
        </div>

        <form onsubmit="event.preventDefault(); alert('AI Assistant demo request sent!');" style="display:flex; gap:0.75rem;">
            <input type="text" placeholder="Ask for fashion advice or product details..." style="flex:1; padding:0.75rem 1rem; border:1px solid #cbd5e1; border-radius:0.5rem; font-size:0.95rem;">
            <button type="submit" class="btn" style="width:auto; padding:0.75rem 1.5rem;">Ask AI</button>
        </form>
    </div>
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

@app.post("/add-to-cart")
def add_to_cart(product_id: str = Form(...)):
    user_id = "user-demo-123"
    try:
        requests.post(f"{CART_SERVICE_URL}/api/cart/items", json={
            "user_id": user_id,
            "item": {"product_id": product_id, "quantity": 1}
        }, timeout=3)
    except Exception:
        pass
    return RedirectResponse(url="/cart", status_code=303)

@app.get("/cart", response_class=HTMLResponse)
def cart_page(request: Request):
    user_currency = request.cookies.get("user_currency", "USD")
    user_id = "user-demo-123"
    items = []
    try:
        r = requests.get(f"{CART_SERVICE_URL}/api/cart/{user_id}", timeout=3)
        items = r.json().get("items", [])
    except Exception:
        pass

    cart_count = sum(item.get("quantity", 1) for item in items)

    if not items:
        content = """
        <div style="text-align:center; padding:4rem 0;">
            <h2 style="font-size:1.75rem; color:#0f172a; font-weight:700;">Your Cart is Empty</h2>
            <p style="color:#64748b; margin:0.75rem 0 1.5rem 0;">Explore our collection and add items to your cart.</p>
            <a href="/" class="btn" style="max-width:220px;">Start Shopping</a>
        </div>
        """
    else:
        items_html = ""
        total = 0
        for item in items:
            subtotal = 50 * item["quantity"]
            total += subtotal
            items_html += f"""
            <div style="display:flex; justify-content:space-between; align-items:center; padding:1rem 0; border-bottom:1px solid #e2e8f0;">
                <div>
                    <h4 style="font-weight:700; color:#0f172a;">Product ID: {item["product_id"]}</h4>
                    <p style="color:#64748b; font-size:0.875rem;">Quantity: {item["quantity"]}</p>
                </div>
                <div style="font-weight:800; color:#ea580c; font-size:1.1rem;">${subtotal}.00 USD</div>
            </div>
            """

        content = f"""
        <h1 style="font-size:2rem; font-weight:800; color:#0f172a; margin-bottom:1.5rem;">Your Shopping Cart</h1>
        <div style="background:#ffffff; padding:2rem; border-radius:1rem; border:1px solid #e2e8f0; box-shadow:0 4px 6px -1px rgba(0,0,0,0.05);">
            {items_html}
            <div style="display:flex; justify-content:space-between; align-items:center; margin-top:2rem; font-size:1.25rem; font-weight:800;">
                <span style="color:#0f172a;">Estimated Total:</span>
                <span style="color:#ea580c;">${total + 15}.00 USD</span>
            </div>
            <form action="/checkout" method="post" style="margin-top:2rem;">
                <button type="submit" class="btn" style="background:#10b981; font-size:1.1rem; padding:1rem;">Proceed to Checkout</button>
            </form>
        </div>
        """

    return HTML_WRAPPER.format(
        title="Your Cart", top_ticker=TOP_ANNOUNCEMENT_TICKER, ad_banner="", content=content,
        footer=FOOTER_HTML, cart_count=cart_count,
        usd_selected="selected" if user_currency=="USD" else "",
        eur_selected="selected" if user_currency=="EUR" else "",
        gbp_selected="selected" if user_currency=="GBP" else "",
        jpy_selected="selected" if user_currency=="JPY" else "",
        cad_selected="selected" if user_currency=="CAD" else "",
        inr_selected="selected" if user_currency=="INR" else ""
    )

@app.post("/checkout", response_class=HTMLResponse)
def process_checkout(request: Request):
    user_currency = request.cookies.get("user_currency", "USD")
    user_id = "user-demo-123"
    try:
        r = requests.post(f"{CHECKOUT_SERVICE_URL}/api/checkout", json={
            "user_id": user_id,
            "user_currency": user_currency,
            "email": "customer@stylehub.com",
            "address": {
                "street_address": "123 Fashion Ave",
                "city": "New York",
                "state": "NY",
                "country": "USA",
                "zip_code": 10001
            },
            "credit_card": {
                "credit_card_number": "4532-1111-2222-3333",
                "credit_card_cvv": 123,
                "credit_card_expiration_year": 2028,
                "credit_card_expiration_month": 12
            }
        }, timeout=8)
        data = r.json()
        
        content = f"""
        <div style="background:#ffffff; padding:3rem; border-radius:1rem; border:1px solid #10b981; text-align:center; max-width:600px; margin:2rem auto; box-shadow:0 10px 25px -5px rgba(16, 185, 129, 0.1);">
            <div style="font-size:3.5rem; margin-bottom:1rem;">🎉</div>
            <h1 style="color:#059669; font-size:2rem; font-weight:800;">Order Confirmed!</h1>
            <p style="color:#64748b; margin-top:0.5rem;">Thank you for shopping with StyleHub.</p>
            <div style="text-align:left; background:#f8fafc; padding:1.5rem; border-radius:0.5rem; margin:2rem 0; font-family:monospace; border:1px solid #e2e8f0; line-height:1.6;">
                <p><strong>Order ID:</strong> {data.get("order_id")}</p>
                <p><strong>Tracking Number:</strong> {data.get("shipping_tracking_id")}</p>
                <p><strong>Total Charged:</strong> {data.get("total_amount")}</p>
                <p><strong>Email Sent To:</strong> {data.get("email")}</p>
            </div>
            <a href="/" class="btn" style="max-width:220px;">Continue Shopping</a>
        </div>
        """
    except Exception as e:
        content = f'<h2 style="color:#ef4444;">Checkout Failed</h2><p>{e}</p>'

    return HTML_WRAPPER.format(
        title="Order Success", top_ticker=TOP_ANNOUNCEMENT_TICKER, ad_banner="", content=content,
        footer=FOOTER_HTML, cart_count=0,
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
