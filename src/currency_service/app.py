"""
StyleHub - Currency Service
gRPC Microservice for multi-currency conversion
"""

from fastapi import FastAPI
from contextlib import asynccontextmanager
import os, sys, concurrent.futures, grpc

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from genproto import stylehub_pb2, stylehub_pb2_grpc

EXCHANGE_RATES = {"USD": 1.0, "EUR": 0.92, "GBP": 0.78, "JPY": 155.0, "CAD": 1.36, "INR": 83.5}

class CurrencyServicer(stylehub_pb2_grpc.CurrencyServiceServicer):
    def GetSupportedCurrencies(self, request, context):
        return stylehub_pb2.GetSupportedCurrenciesResponse(currency_codes=list(EXCHANGE_RATES.keys()))

    def Convert(self, request, context):
        from_code, to_code = request.from_money.currency_code.upper(), request.to_code.upper()
        if from_code not in EXCHANGE_RATES or to_code not in EXCHANGE_RATES:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            return stylehub_pb2.Money()

        usd = (request.from_money.units + request.from_money.nanos / 1e9) / EXCHANGE_RATES[from_code]
        converted = usd * EXCHANGE_RATES[to_code]
        units = int(converted)
        nanos = int((converted - units) * 1e9)
        return stylehub_pb2.Money(currency_code=to_code, units=units, nanos=nanos)

@asynccontextmanager
async def lifespan(app: FastAPI):
    grpc_server = grpc.server(concurrent.futures.ThreadPoolExecutor(max_workers=10))
    stylehub_pb2_grpc.add_CurrencyServiceServicer_to_server(CurrencyServicer(), grpc_server)
    grpc_port = int(os.getenv("GRPC_PORT", "50053"))
    grpc_server.add_insecure_port(f"[::]:{grpc_port}")
    grpc_server.start()
    print(f"⚡ CurrencyService gRPC active on port {grpc_port}")
    yield
    grpc_server.stop(grace=None)

app = FastAPI(title="StyleHub Currency Service", lifespan=lifespan)

@app.get("/healthz")
def health_check():
    return {"status": "ok", "service": "currency-service"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8083")))
