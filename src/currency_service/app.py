"""
StyleHub - Currency Service
Custom Python Microservice for multi-currency conversion with gRPC Support
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import os, sys, concurrent.futures, grpc

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from genproto import stylehub_pb2, stylehub_pb2_grpc

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

def perform_conversion(from_code: str, to_code: str, units: int, nanos: int) -> tuple:
    from_code = from_code.upper()
    to_code = to_code.upper()
    if from_code not in EXCHANGE_RATES or to_code not in EXCHANGE_RATES:
        raise ValueError(f"Unsupported currency conversion {from_code} -> {to_code}")
    total_from = units + (nanos / 1e9)
    usd_amount = total_from / EXCHANGE_RATES[from_code]
    target_amount = usd_amount * EXCHANGE_RATES[to_code]
    new_units = int(target_amount)
    new_nanos = int((target_amount - new_units) * 1e9)
    return new_units, new_nanos

class CurrencyServicer(stylehub_pb2_grpc.CurrencyServiceServicer):
    def GetSupportedCurrencies(self, request, context):
        return stylehub_pb2.GetSupportedCurrenciesResponse(currency_codes=list(EXCHANGE_RATES.keys()))

    def Convert(self, request, context):
        try:
            units, nanos = perform_conversion(
                request.from_money.currency_code, request.to_code,
                request.from_money.units, request.from_money.nanos
            )
            return stylehub_pb2.Money(currency_code=request.to_code.upper(), units=units, nanos=nanos)
        except Exception as e:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(e))
            return stylehub_pb2.Money()

grpc_server = None

@app.on_event("startup")
def startup_event():
    global grpc_server
    grpc_server = grpc.server(concurrent.futures.ThreadPoolExecutor(max_workers=10))
    stylehub_pb2_grpc.add_CurrencyServiceServicer_to_server(CurrencyServicer(), grpc_server)
    grpc_port = int(os.getenv("GRPC_PORT", "50053"))
    grpc_server.add_insecure_port(f"[::]:{grpc_port}")
    grpc_server.start()
    print(f"CurrencyService gRPC server running on port {grpc_port}")

@app.on_event("shutdown")
def shutdown_event():
    global grpc_server
    if grpc_server:
        grpc_server.stop(grace=None)

@app.get("/healthz")
def health_check():
    return {"status": "ok", "service": "currency-service", "grpc_port": os.getenv("GRPC_PORT", "50053")}

@app.get("/api/currencies", response_model=List[str])
def get_supported_currencies():
    return list(EXCHANGE_RATES.keys())

@app.post("/api/currency/convert", response_model=Money)
def convert_currency(request: CurrencyConversionRequest):
    try:
        units, nanos = perform_conversion(
            request.from_money.currency_code, request.to_code,
            request.from_money.units, request.from_money.nanos
        )
        return Money(currency_code=request.to_code.upper(), units=units, nanos=nanos)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8083"))
    uvicorn.run(app, host="0.0.0.0", port=port)
