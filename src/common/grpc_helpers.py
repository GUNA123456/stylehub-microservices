"""
StyleHub Common gRPC Helpers & Utility Functions
Shared Protobuf conversions across microservices
"""

def create_money_pb(pb_module, currency_code: str = "USD", units: int = 0, nanos: int = 0):
    return pb_module.Money(
        currency_code=currency_code,
        units=units,
        nanos=nanos
    )

def create_cart_item_pb(pb_module, product_id: str, quantity: int):
    return pb_module.CartItem(
        product_id=product_id,
        quantity=quantity
    )
