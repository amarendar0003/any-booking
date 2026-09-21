"""
Abstract base class for all payment gateways.

To add a new country/gateway:
  1. Create payments/gateways/<slug>_gateway.py implementing BasePaymentGateway
  2. Add it to GATEWAY_REGISTRY in payments/gateways/registry.py
  3. Add the gateway slug to PaymentGatewayConfig.GATEWAY_CHOICES
  4. Create templates/payments/checkout_<slug>.html
  5. Store the gateway's API credentials in .env / Secret Manager
  6. In Admin → Payment Gateway Configs, set the country's gateway and enable it
"""


class BasePaymentGateway:
    """
    Contract that every payment gateway must fulfil.
    All monetary amounts are in major units (e.g. 150.00 INR, not 15000 paise).
    """
    slug = ''           # matches PaymentGatewayConfig.gateway choices
    display_name = ''   # shown to customers
    checkout_template = ''  # e.g. 'payments/checkout_razorpay.html'

    # ── Required to implement ─────────────────────────────────────────────────

    def create_order(self, booking) -> dict:
        """
        Create a payment order with the gateway and return a dict:
          {
            'order_id': str,   # gateway's order/session ID (stored as gateway_order_id)
            'amount':   Decimal,
            'currency': str,   # ISO 4217, e.g. 'INR'
          }
        Raise GatewayError on failure.
        """
        raise NotImplementedError

    def verify_callback(self, post_data: dict) -> bool:
        """
        Verify the signature/integrity of the gateway callback POST data.
        Return True if the payment is genuine and captured.
        """
        raise NotImplementedError

    def get_checkout_context(self, booking, payment) -> dict:
        """
        Return extra template context variables for checkout_template.
        The view always passes 'booking' and 'payment' — add gateway-specific vars here.
        """
        raise NotImplementedError

    def extract_order_id(self, post_data: dict) -> str:
        """
        Pull the gateway_order_id out of the callback POST data so the view
        can look up the Payment record.
        """
        raise NotImplementedError

    # ── Optional helpers ──────────────────────────────────────────────────────

    def get_currency(self, country) -> str:
        """Return the ISO currency code for the given country."""
        return country.currency if hasattr(country, 'currency') else 'INR'

    def post_capture_hook(self, payment, post_data: dict):
        """
        Called after a successful capture before the view redirects.
        Override to store gateway-specific IDs (e.g. Razorpay payment_id).
        Default: no-op.
        """


class GatewayError(Exception):
    """Raised when a gateway API call fails."""
