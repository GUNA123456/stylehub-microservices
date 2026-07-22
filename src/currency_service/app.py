"""
StyleHub - Currency Service
Custom Python Microservice for multi-currency conversion
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import os

app = FastAPI(
    title="StyleHub Currency Service",
    description="Provides real-time multi-currency conversions for StyleHub",
    version="1.0.0"
)

class Money(BaseModel):
    currency_code: str
    units: int
    nanos: int = 0

class CurrencyConversionRequest(BaseModel):
    from_money: Money
    to_code: str

# Standard currency exchange rates against USD base
EXCHANGE_RATES = {
    "USD": 1.0,
    "EUR": 0.92,
    "GBP": 0.78,
    "JPY": 155.0,
    "CAD": 1.36,
    "INR": 83.5
}

@app.get("/healthz")
def health_check():
    return {"status": "ok", "service": "currency-service"}

@app.get("/api/currencies", response_model=List[str])
def get_supported_currencies():
    """Returns a list of supported 3-letter ISO currency codes."""
    return list(EXCHANGE_RATES.keys())

@app.post("/api/currency/convert", response_model=Money)
def convert_currency(request: CurrencyConversionRequest):
    """Converts money from one currency to another."""
    from_code = request.from_money.currency_code.upper()
    to_code = request.to_code.upper()

    if from_code not in EXCHANGE_RATES:
        raise HTTPException(status_code=400, detail=f"Unsupported currency code '{from_code}'")
    if to_code not in EXCHANGE_RATES:
        raise HTTPException(status_code=400, detail=f"Unsupported target currency code '{to_code}'")

    # Convert total amount to float USD
    total_from = request.from_money.units + (request.from_money.nanos / 1e9)
    usd_amount = total_from / EXCHANGE_RATES[from_code]
    
    # Convert USD to target currency
    target_amount = usd_amount * EXCHANGE_RATES[to_code]
    
    target_units = int(target_amount)
    target_nanos = int((target_amount - target_units) * 1e9)

    return Money(
        currency_code=to_code,
        units=target_units,
        nanos=target_nanos
    )

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8083"))
    uvicorn.run(app, host="0.0.0.0", port=port)
