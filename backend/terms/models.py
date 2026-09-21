"""
Terms of Use — feature-flagged per site and/or per service.

is_active is the feature flag. When no active terms apply to a booking,
the customer proceeds without any acceptance step.

Scope:
  site    — shown on every booking regardless of service
  service — shown only for bookings of a specific service

If both a site-wide and a service-specific term are active, the customer
must accept both (they are shown together, one combined checkbox).
"""
from django.db import models


class TermsOfUse(models.Model):
    SCOPE_SITE = 'site'
    SCOPE_SERVICE = 'service'
    SCOPE_CHOICES = [
        (SCOPE_SITE,    'Site-wide (all bookings)'),
        (SCOPE_SERVICE, 'Service-specific'),
    ]

    title = models.CharField(max_length=200)
    content = models.TextField(
        help_text='HTML is supported. Keep it concise — the full text is shown '
                  'in a scrollable box during booking.'
    )
    version = models.CharField(
        max_length=50,
        help_text='e.g. v1.0 or 2024-01. Snapshot at acceptance time for audit.',
    )
    scope = models.CharField(max_length=20, choices=SCOPE_CHOICES, default=SCOPE_SITE)
    service = models.ForeignKey(
        'services.Service',
        null=True, blank=True,
        on_delete=models.CASCADE,
        related_name='terms',
        help_text='Required when scope = Service-specific; ignored for Site-wide.',
    )
    is_active = models.BooleanField(
        default=False,
        help_text='Enable to require acceptance during booking. '
                  'Disable to stop showing this terms document without deleting it.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Terms of Use'
        verbose_name_plural = 'Terms of Use'
        ordering = ['scope', 'title']

    def __str__(self):
        flag = '✅' if self.is_active else '⏸'
        if self.scope == self.SCOPE_SERVICE and self.service:
            return f'{flag} {self.title} (v{self.version}) — {self.service.name}'
        return f'{flag} {self.title} (v{self.version}) — Site-wide'

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.scope == self.SCOPE_SERVICE and not self.service_id:
            raise ValidationError({'service': 'A service must be selected for service-specific terms.'})
        if self.scope == self.SCOPE_SITE:
            self.service = None


class TermsAcceptance(models.Model):
    """Immutable record of a customer accepting terms at booking time."""
    booking = models.ForeignKey(
        'bookings.Booking',
        on_delete=models.PROTECT,
        related_name='terms_acceptances',
    )
    terms = models.ForeignKey(
        TermsOfUse,
        on_delete=models.PROTECT,
        related_name='acceptances',
    )
    version_at_acceptance = models.CharField(
        max_length=50,
        help_text='Snapshot of TermsOfUse.version at the time of acceptance.',
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    accepted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Terms Acceptance'
        verbose_name_plural = 'Terms Acceptances'
        ordering = ['-accepted_at']

    def __str__(self):
        return (
            f'Booking #{self.booking_id} accepted "{self.terms.title}" '
            f'v{self.version_at_acceptance} at {self.accepted_at:%Y-%m-%d %H:%M}'
        )
