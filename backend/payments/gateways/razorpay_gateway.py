"""
Razorpay gateway — India (INR, UPI, Cards, Net Banking, Wallets).

Required environment variables:
  RAZORPAY_KEY_ID      — from Razorpay Dashboard → Settings → API Keys
  RAZORPAY_KEY_SECRET  — keep in Secret Manager, never commit

Docs: https://razorpay.com/docs/payments/payment-gateway/
"""
import hmac
import hashlib

import razorpay
from django.conf import settings

from .base import BasePaymentGateway, GatewayError


class RazorpayGateway(BasePaymentGateway):
    slug = 'razorpay'
    display_name = 'Razorpay'
    checkout_template = 'payments/checkout_razorpay.html'

    def _client(self):
        key_id = getattr(settings, 'RAZORPAY_KEY_ID', '')
        key_secret = getattr(settings, 'RAZORPAY_KEY_SECRET', '')
        if not key_id or not key_secret:
            raise GatewayError('RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET not configured')
        return razorpay.Client(auth=(key_id, key_secret))

    def create_order(self, booking) -> dict:
        try:
            client = self._client()
            currency = self.get_currency(booking.service.city.country) if booking.service.city else 'INR'
            # Razorpay requires amount in smallest currency unit (paise for INR)
            amount_minor = int(booking.total_amount * 100)
            order = client.order.create({
                'amount': amount_minor,
                'currency': currency,
                'receipt': f'booking_{booking.pk}',
                'notes': {
                    'customer_name': booking.customer_name,
                    'service': booking.service.name,
                },
            })
        except GatewayError:
            raise
        except Exception as exc:
            raise GatewayError(f'Razorpay create_order failed: {exc}') from exc

        return {
            'order_id': order['id'],
            'amount': booking.total_amount,
            'currency': currency,
        }

    def get_checkout_context(self, booking, payment) -> dict:
        return {
            'razorpay_key': settings.RAZORPAY_KEY_ID,
            'razorpay_order_id': payment.gateway_order_id,
            'amount_minor': int(payment.amount * 100),
            'currency': payment.currency,
        }

    def verify_callback(self, post_data: dict) -> bool:
        order_id = post_data.get('razorpay_order_id', '')
        payment_id = post_data.get('razorpay_payment_id', '')
        signature = post_data.get('razorpay_signature', '')

        msg = f'{order_id}|{payment_id}'
        expected = hmac.new(
            settings.RAZORPAY_KEY_SECRET.encode(),
            msg.encode(),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    def extract_order_id(self, post_data: dict) -> str:
        return post_data.get('razorpay_order_id', '')

    def post_capture_hook(self, payment, post_data: dict):
        payment.razorpay_payment_id = post_data.get('razorpay_payment_id', '')
        payment.razorpay_signature = post_data.get('razorpay_signature', '')
        payment.save(update_fields=['razorpay_payment_id', 'razorpay_signature', 'updated_at'])
