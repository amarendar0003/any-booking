"""
Email sending utilities for the booking workflow.

Every email sent is recorded in EmailLog regardless of success/failure.
Recipient resolution for admin notifications:
  1. Super-admin: settings.ADMIN_NOTIFY_EMAIL (if set)
  2. Area admins: StaffProfile holders whose location scope covers the booking's city
"""
import logging
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


# ── Recipient resolution ──────────────────────────────────────────────────────

def _admin_recipients(booking):
    """
    Returns a list of (name, email) tuples for all admins who should be
    notified about this booking:
      - The ADMIN_NOTIFY_EMAIL superadmin address (if configured)
      - Any StaffProfile user whose location scope covers the booking city
    """
    from django.contrib.auth.models import User
    from django.db.models import Q
    from services.models import StaffProfile

    recipients = []

    # Global super-admin address from settings
    if settings.ADMIN_NOTIFY_EMAIL:
        recipients.append(('Admin', settings.ADMIN_NOTIFY_EMAIL))

    # Area admins via StaffProfile
    city = booking.service.city if booking.service else None
    if city:
        state = city.state
        country = city.country
        profiles = StaffProfile.objects.filter(
            Q(city=city) |
            Q(city__isnull=True, state=state) |
            Q(city__isnull=True, state__isnull=True, country=country)
        ).select_related('user')
        for profile in profiles:
            user = profile.user
            if user.email and user.is_active and user.is_staff:
                name = user.get_full_name() or user.username
                addr = (name, user.email)
                if addr not in recipients:
                    recipients.append(addr)

    return recipients


# ── Core send function ────────────────────────────────────────────────────────

def _send(booking, email_type, recipient_name, recipient_email,
          subject, template_name, context, sent_by=None):
    """Render template, send email, and write an EmailLog record."""
    from .models import EmailLog

    context.setdefault('site_url', getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000'))
    context.setdefault('booking', booking)

    body_html = render_to_string(f'emails/{template_name}', context)
    # Plain-text fallback — strip tags roughly
    import re
    body_text = re.sub(r'<[^>]+>', ' ', body_html)
    body_text = re.sub(r'[ \t]+', ' ', body_text).strip()

    status = EmailLog.STATUS_SENT
    error_msg = ''
    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=body_text,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[f'{recipient_name} <{recipient_email}>'] if recipient_name else [recipient_email],
        )
        msg.attach_alternative(body_html, 'text/html')
        msg.send()
    except Exception as exc:
        status = EmailLog.STATUS_FAILED
        error_msg = str(exc)
        logger.error('Email send failed [%s] to %s: %s', email_type, recipient_email, exc)

    EmailLog.objects.create(
        booking=booking,
        email_type=email_type,
        recipient_email=recipient_email,
        recipient_name=recipient_name,
        subject=subject,
        body_html=body_html,
        status=status,
        error_message=error_msg,
        sent_by=sent_by,
    )
    return status == EmailLog.STATUS_SENT


# ── Public API ────────────────────────────────────────────────────────────────

def send_booking_received(booking):
    """
    Triggered when a booking is first submitted.
    Sends:
      1. Confirmation to the customer
      2. New-booking alert to super-admin + area admins
    """
    from .models import EmailLog

    ctx = {'booking': booking}

    # 1. Customer confirmation (email is optional — skip if not provided)
    if booking.customer_email:
        _send(
            booking=booking,
            email_type=EmailLog.TYPE_BOOKING_RECEIVED,
            recipient_name=booking.customer_name,
            recipient_email=booking.customer_email,
            subject=f'Booking Request Received [{booking.confirmation_number}] — {booking.service.name}',
            template_name='booking_received.html',
            context=ctx,
        )

    # 2. Admin alerts
    for name, email in _admin_recipients(booking):
        _send(
            booking=booking,
            email_type=EmailLog.TYPE_ADMIN_NOTIFY,
            recipient_name=name,
            recipient_email=email,
            subject=f'[AnyBooking] New Booking {booking.confirmation_number} — {booking.service.name}',
            template_name='admin_notify.html',
            context=ctx,
        )

    # 3. Vendor alert
    vendor = _vendor_recipient(booking)
    if vendor:
        _send(
            booking=booking,
            email_type=EmailLog.TYPE_VENDOR_RECEIVED,
            recipient_name=vendor[0],
            recipient_email=vendor[1],
            subject=f'[AnyBooking] New Booking Request {booking.confirmation_number} — {booking.service.name}',
            template_name='vendor_booking_received.html',
            context=ctx,
        )


def _vendor_recipient(booking):
    """Return (name, email) for the vendor if notifications are enabled, else None."""
    vendor = booking.service.vendor
    if vendor.notify_on_booking and vendor.email:
        return (vendor.name, vendor.email)
    return None


def send_booking_approved(booking, sent_by=None):
    """
    Triggered when an admin confirms/approves a booking.
    Sends approval email to the customer, and to the vendor if notifications are enabled.
    """
    from .models import EmailLog

    if booking.customer_email:
        _send(
            booking=booking,
            email_type=EmailLog.TYPE_APPROVED,
            recipient_name=booking.customer_name,
            recipient_email=booking.customer_email,
            subject=f'Booking Confirmed [{booking.confirmation_number}] — {booking.service.name}',
            template_name='booking_approved.html',
            context={'booking': booking},
            sent_by=sent_by,
        )

    vendor = _vendor_recipient(booking)
    if vendor:
        _send(
            booking=booking,
            email_type=EmailLog.TYPE_VENDOR_CONFIRMED,
            recipient_name=vendor[0],
            recipient_email=vendor[1],
            subject=f'[AnyBooking] Booking Confirmed [{booking.confirmation_number}] — {booking.service.name}',
            template_name='vendor_booking_confirmed.html',
            context={'booking': booking},
            sent_by=sent_by,
        )


def send_cancellation_request(booking):
    """
    Triggered when a customer submits a cancellation request.
    Sends:
      1. Acknowledgement to the customer
      2. Alert to super-admin + area admins
    """
    from .models import EmailLog

    ctx = {'booking': booking}

    _send(
        booking=booking,
        email_type=EmailLog.TYPE_CANCEL_REQUEST_CUSTOMER,
        recipient_name=booking.customer_name,
        recipient_email=booking.customer_email,
        subject=f'Cancellation Request Received [{booking.confirmation_number}] — {booking.service.name}',
        template_name='cancellation_request_customer.html',
        context=ctx,
    )

    for name, email in _admin_recipients(booking):
        _send(
            booking=booking,
            email_type=EmailLog.TYPE_CANCEL_REQUEST_ADMIN,
            recipient_name=name,
            recipient_email=email,
            subject=f'[AnyBooking] Cancellation Requested {booking.confirmation_number} — {booking.service.name}',
            template_name='cancellation_request_admin.html',
            context=ctx,
        )


def send_booking_cancelled(booking, sent_by=None):
    """
    Triggered when an admin cancels a booking.
    Sends cancellation + refund details to the customer, and a notice to the vendor if enabled.
    """
    from .models import EmailLog

    if booking.customer_email:
        _send(
            booking=booking,
            email_type=EmailLog.TYPE_CANCELLED,
            recipient_name=booking.customer_name,
            recipient_email=booking.customer_email,
            subject=f'Booking Cancelled [{booking.confirmation_number}] — {booking.service.name}',
            template_name='booking_cancelled.html',
            context={'booking': booking},
            sent_by=sent_by,
        )

    vendor = _vendor_recipient(booking)
    if vendor:
        _send(
            booking=booking,
            email_type=EmailLog.TYPE_VENDOR_CANCELLED,
            recipient_name=vendor[0],
            recipient_email=vendor[1],
            subject=f'[AnyBooking] Booking Cancelled [{booking.confirmation_number}] — {booking.service.name}',
            template_name='vendor_booking_cancelled.html',
            context={'booking': booking},
            sent_by=sent_by,
        )
