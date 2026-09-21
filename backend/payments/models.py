from django.db import models
from bookings.models import Booking
from services.models import Country


class PaymentGatewayConfig(models.Model):
    """
    Feature-flagged, per-country payment gateway configuration.
    One row per country. Set is_enabled=False to disable online payments
    for that country (bookings proceed as offline/cash).

    API credentials are NOT stored here — they live in environment
    variables / Secret Manager, keyed by gateway slug.
    Add a new gateway by:
      1. Adding a GATEWAY_* constant + GATEWAY_CHOICES entry
      2. Creating payments/gateways/<slug>_gateway.py
      3. Registering it in payments/gateways/registry.py
    """
    GATEWAY_RAZORPAY = 'razorpay'
    GATEWAY_STRIPE = 'stripe'
    GATEWAY_CASHFREE = 'cashfree'
    GATEWAY_PAYSTACK = 'paystack'

    GATEWAY_CHOICES = [
        (GATEWAY_RAZORPAY, 'Razorpay (India — UPI, Cards, Net Banking)'),
        (GATEWAY_STRIPE,   'Stripe (International — Cards)'),
        (GATEWAY_CASHFREE, 'Cashfree (India/SEA)'),
        (GATEWAY_PAYSTACK, 'Paystack (Africa)'),
    ]

    country = models.OneToOneField(
        Country, on_delete=models.CASCADE, related_name='payment_config'
    )
    gateway = models.CharField(max_length=30, choices=GATEWAY_CHOICES)
    is_enabled = models.BooleanField(
        default=False,
        help_text='Enable to redirect customers to the payment gateway after booking. '
                  'Disable for offline/cash bookings.'
    )
    display_name = models.CharField(
        max_length=100, blank=True,
        help_text='Override the gateway label shown to customers (e.g. "Pay Online")'
    )
    notes = models.TextField(blank=True, help_text='Internal notes — not shown to customers')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Payment Gateway Config'
        verbose_name_plural = 'Payment Gateway Configs'
        ordering = ['country__name']

    def __str__(self):
        status = '✅ enabled' if self.is_enabled else '⏸ disabled'
        return f'{self.country} → {self.get_gateway_display()} ({status})'

    def get_customer_label(self):
        return self.display_name or self.get_gateway_display()


class Payment(models.Model):
    STATUS_CREATED = 'created'
    STATUS_CAPTURED = 'captured'
    STATUS_FAILED = 'failed'
    STATUS_REFUNDED = 'refunded'

    STATUS_CHOICES = [
        (STATUS_CREATED,  'Created'),
        (STATUS_CAPTURED, 'Captured'),
        (STATUS_FAILED,   'Failed'),
        (STATUS_REFUNDED, 'Refunded'),
    ]

    booking = models.ForeignKey(Booking, on_delete=models.PROTECT, related_name='payments')

    # Which gateway processed this payment
    gateway = models.CharField(
        max_length=30,
        choices=PaymentGatewayConfig.GATEWAY_CHOICES,
        default=PaymentGatewayConfig.GATEWAY_RAZORPAY,
    )

    # Generic order/session identifier from the gateway (previously razorpay_order_id)
    gateway_order_id = models.CharField(max_length=200, unique=True)

    # Razorpay-specific fields (populated only for gateway='razorpay')
    razorpay_payment_id = models.CharField(max_length=100, blank=True)
    razorpay_signature = models.CharField(max_length=255, blank=True)

    amount = models.DecimalField(max_digits=12, decimal_places=2, help_text='Amount in local currency')
    currency = models.CharField(max_length=10, default='INR')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_CREATED)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.gateway.upper()} {self.gateway_order_id} — Booking #{self.booking_id} ({self.status})'
