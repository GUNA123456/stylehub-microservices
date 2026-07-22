#!/bin/bash
# StyleHub Native Local Microservices Launcher
# Runs all 10 Python microservices locally with native gRPC support

echo "🚀 Setting up StyleHub local Python environment & compiling gRPC stubs..."
python3 -m venv venv
source venv/bin/activate
pip install --quiet fastapi uvicorn pydantic requests redis python-multipart grpcio grpcio-tools protobuf

# Compile Protobuf definitions
./gen_proto.sh

echo "⚡ Starting StyleHub Microservices (REST + gRPC)..."

PORT=8081 GRPC_PORT=50051 python3 src/product_catalog_service/app.py &
PORT=8082 GRPC_PORT=50052 python3 src/cart_service/app.py &
PORT=8083 GRPC_PORT=50053 python3 src/currency_service/app.py &
PORT=8084 GRPC_PORT=50054 python3 src/recommendation_service/app.py &
PORT=8085 GRPC_PORT=50055 python3 src/shipping_service/app.py &
PORT=8086 GRPC_PORT=50056 python3 src/checkout_service/app.py &
PORT=8087 GRPC_PORT=50057 python3 src/ad_service/app.py &
PORT=8088 GRPC_PORT=50058 python3 src/email_service/app.py &
PORT=8089 GRPC_PORT=50059 python3 src/payment_service/app.py &
PORT=8080 python3 src/frontend/app.py &

echo "✅ All StyleHub Microservices Started!"
echo "👉 Open your browser at: http://localhost:8080"
echo "Press Ctrl+C to stop all services."
wait
