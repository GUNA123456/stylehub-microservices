#!/usr/bin/env bash
# Python gRPC Stubs for StyleHub Microservices

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROTO_DIR="${SCRIPT_DIR}/protos"
PROTO_FILE="${PROTO_DIR}/stylehub.proto"

echo "Compiling ${PROTO_FILE}..."

# Generate stubs in root
python3 -m grpc_tools.protoc \
    -I="${PROTO_DIR}" \
    --python_out="${SCRIPT_DIR}" \
    --grpc_python_out="${SCRIPT_DIR}" \
    "${PROTO_FILE}"

echo "Copying generated gRPC stubs to microservices..."
SERVICES=(
    "ad_service"
    "cart_service"
    "checkout_service"
    "currency_service"
    "email_service"
    "frontend"
    "payment_service"
    "product_catalog_service"
    "recommendation_service"
    "shipping_service"
)

for service in "${SERVICES[@]}"; do
    mkdir -p "${SCRIPT_DIR}/src/${service}/genproto"
    cp "${SCRIPT_DIR}/stylehub_pb2.py" "${SCRIPT_DIR}/src/${service}/genproto/"
    cp "${SCRIPT_DIR}/stylehub_pb2_grpc.py" "${SCRIPT_DIR}/src/${service}/genproto/"
    touch "${SCRIPT_DIR}/src/${service}/genproto/__init__.py"
    # Fix import path inside package
    sed -i '' 's/import stylehub_pb2 as stylehub__pb2/from . import stylehub_pb2 as stylehub__pb2/g' "${SCRIPT_DIR}/src/${service}/genproto/stylehub_pb2_grpc.py"
done

# Cleanup temporary root stubs
rm -f "${SCRIPT_DIR}/stylehub_pb2.py" "${SCRIPT_DIR}/stylehub_pb2_grpc.py"

echo "gRPC compilation and stub distribution complete!"
