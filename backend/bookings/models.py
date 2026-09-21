import secrets
import string

from django.db import models
from django.contrib.auth.models import User
from services.models import Service

_CONF_CHARS = (string.ascii_uppercase.replace('I', '').replace('O', '')
               + string.digits.replace('0', '').replace('1', ''))


def _generate_confirmation_number():
    """Return a unique 8-character confirmation code, e.g. AB-K3M7X9QP."""
    code = ''.join(secrets.choice(_CONF_CHARS) for _ in range(8))
    return f'AB-{code}'


class Booking(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_CANCELLED = 'cancelled'
    STATUS_COMPLETED = 'completed'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_CONFIRMED, 'Confirmed'),
        (STATUS_CANCELLED, 'Cancelled'),
        (STATUS_COMPLETED, 'Completed'),
    ]

    REFUND_NONE = 'none'
    REFUND_PARTIAL = 'partial'
    REFUND_FULL = 'full'
    REFUND_CHOICES = [
        (REFUND_NONE, 'No Refund'),
        (REFUND_PARTIAL, 'Partial Refund'),
        (REFUND_FULL, 'Full Refund'),
    ]

    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name='bookings')

    confirmation_number = models.CharField(
        max_length=20, unique=True, blank=True,
        help_text='Auto-generated unique reference shown to the customer (e.g. AB-K3M7X9QP).',
    )

    # Customer info (no user account needed — admin manages)
    customer_name = models.CharField(max_length=200)
    customer_email = models.EmailField(blank=True, default='')
    customer_phone = models.CharField(max_length=20)

    event_date = models.DateField()
    event_end_date = models.DateField(null=True, blank=True, help_text='For multi-day bookings')
    event_time = models.TimeField(null=True, blank=True)
    guest_count = models.PositiveIntegerField(default=1)
    special_requests = models.TextField(blank=True)

    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    advance_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    admin_notes = models.TextField(blank=True)

    # Cancellation / refund (admin-side)
    refund_type = models.CharField(max_length=10, choices=REFUND_CHOICES, default=REFUND_NONE, blank=True)
    refund_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True,
                                        help_text='Actual refund amount (leave blank for no refund)')
    cancellation_reason = models.TextField(blank=True, help_text='Reason shown to the customer')

    # Customer-initiated cancellation request
    cancellation_requested = models.BooleanField(default=False)
    cancellation_request_reason = models.TextField(blank=True)
    cancellation_requested_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.confirmation_number} – {self.customer_name} – {self.service.name} on {self.event_date}'

    def save(self, *args, **kwargs):
        if not self.confirmation_number:
            # Retry on the rare collision chance
            for _ in range(10):
                candidate = _generate_confirmation_number()
                if not Booking.objects.filter(confirmation_number=candidate).exists():
                    self.confirmation_number = candidate
                    break
        super().save(*args, **kwargs)

    @property
    def balance_amount(self):
        return self.total_amount - self.advance_amount


class EmailLog(models.Model):
    """Audit trail for every email sent by the platform."""
    TYPE_BOOKING_RECEIVED = 'booking_received'
    TYPE_ADMIN_NOTIFY = 'admin_notify'
    TYPE_APPROVED = 'booking_approved'
    TYPE_CANCELLED = 'booking_cancelled'
    TYPE_CANCEL_REQUEST_CUSTOMER = 'cancel_request_customer'
    TYPE_CANCEL_REQUEST_ADMIN = 'cancel_request_admin'
    TYPE_VENDOR_RECEIVED = 'vendor_received'
    TYPE_VENDOR_CONFIRMED = 'vendor_confirmed'
    TYPE_VENDOR_CANCELLED = 'vendor_cancelled'

    EMAIL_TYPE_CHOICES = [
        (TYPE_BOOKING_RECEIVED, 'Booking Received (customer)'),
        (TYPE_ADMIN_NOTIFY, 'New Booking Notification (admin)'),
        (TYPE_APPROVED, 'Booking Approved (customer)'),
        (TYPE_CANCELLED, 'Booking Cancelled (customer)'),
        (TYPE_CANCEL_REQUEST_CUSTOMER, 'Cancellation Request (customer)'),
        (TYPE_CANCEL_REQUEST_ADMIN, 'Cancellation Request (admin)'),
        (TYPE_VENDOR_RECEIVED, 'New Booking Received (vendor)'),
        (TYPE_VENDOR_CONFIRMED, 'Booking Confirmed (vendor)'),
        (TYPE_VENDOR_CANCELLED, 'Booking Cancelled (vendor)'),
    ]

    STATUS_SENT = 'sent'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = [
        (STATUS_SENT, 'Sent'),
        (STATUS_FAILED, 'Failed'),
    ]

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='email_logs')
    email_type = models.CharField(max_length=30, choices=EMAIL_TYPE_CHOICES)
    recipient_email = models.EmailField()
    recipient_name = models.CharField(max_length=200, blank=True)
    subject = models.CharField(max_length=300)
    body_html = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_SENT)
    error_message = models.TextField(blank=True)
    sent_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL,
                                 related_name='sent_emails',
                                 help_text='Admin user who triggered the email (null = system)')
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-sent_at']
        verbose_name = 'Email Log'
        verbose_name_plural = 'Email Logs'

    def __str__(self):
        return f'{self.get_email_type_display()} → {self.recipient_email} ({self.sent_at:%d %b %Y %H:%M})'


class BlockedDate(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='blocked_dates')
    date = models.DateField()
    reason = models.CharField(max_length=200, blank=True)

    class Meta:
        unique_together = ('service', 'date')
        ordering = ['date']

    def __str__(self):
        return f'{self.service.name} blocked on {self.date}'
