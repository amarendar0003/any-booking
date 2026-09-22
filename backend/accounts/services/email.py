"""
Email service for account verification.
Uses Django's EmailMultiAlternatives backed by Brevo SMTP.
"""
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def send_otp_email(user, otp_code: str) -> None:
    """
    Send a 6-digit OTP verification email to ``user`` via Brevo SMTP.

    Raises on delivery failure so the caller can handle it — do NOT
    silently swallow errors in development.
    """
    site_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')
    from_name = getattr(settings, 'BREVO_FROM_NAME', 'AnyBooking')
    from_email = settings.DEFAULT_FROM_EMAIL

    context = {
        'otp_code': otp_code,
        'expires_minutes': 5,
        'user_email': user.email,
        'site_url': site_url,
        'from_name': from_name,
    }

    text_content = render_to_string('emails/verify_otp.txt', context)
    html_content = render_to_string('emails/verify_otp.html', context)

    msg = EmailMultiAlternatives(
        subject='Your AnyBooking verification code',
        body=text_content,
        from_email=from_email,
        to=[user.email],
    )
    msg.attach_alternative(html_content, 'text/html')

    try:
        msg.send(fail_silently=False)
        logger.info('OTP email sent to %s', user.email)
    except Exception:
        logger.exception('Failed to send OTP email to %s', user.email)
        raise
