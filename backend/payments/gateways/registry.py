"""
Gateway registry — maps slug → gateway class and resolves the gateway for a country.

To add a new gateway:
  1. Create payments/gateways/<slug>_gateway.py
  2. Import the class below and add it to GATEWAY_REGISTRY
  3. Add the slug to PaymentGatewayConfig.GATEWAY_CHOICES in models.py
"""
from .base import GatewayError
from .razorpay_gateway import RazorpayGateway

GATEWAY_REGISTRY: dict = {
    RazorpayGateway.slug: RazorpayGateway,
}


def get_gateway_for_country(country):
    """
    Return an instantiated gateway for the given country, or None if
    online payments are disabled / not configured for that country.

    Raises GatewayError if the configured gateway slug is not in the registry.
    """
    try:
        config = country.payment_config
    except Exception:
        return None

    if not config.is_enabled:
        return None

    cls = GATEWAY_REGISTRY.get(config.gateway)
    if cls is None:
        raise GatewayError(
            f"Gateway '{config.gateway}' is configured for {country} "
            f"but has no implementation in GATEWAY_REGISTRY."
        )
    return cls()
