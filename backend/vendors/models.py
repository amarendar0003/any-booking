from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


# ── Service Management: outsourced service vendors ─────────────────────────

class ServiceVendor(models.Model):
    """A third-party service provider that this Vendor outsources work to
    (e.g. a catering company or decorator the venue regularly hires out).
    This is separate from `services.Service`, which is the vendor's own
    bookable listing on the platform.
    """
    CATERING = 'catering'
    DECORATIONS = 'decorations'
    PHOTOGRAPHY = 'photography'
    MUSIC_DJ = 'music_dj'
    LIGHTING = 'lighting'
    TRANSPORT = 'transport'
    MAKEUP_STYLING = 'makeup_styling'
    ANCHORING = 'anchoring'
    OTHER = 'other'

    SERVICE_TYPE_CHOICES = [
        (CATERING, 'Catering'),
        (DECORATIONS, 'Decorations'),
        (PHOTOGRAPHY, 'Photography & Videography'),
        (MUSIC_DJ, 'Music / DJ'),
        (LIGHTING, 'Lighting'),
        (TRANSPORT, 'Transport'),
        (MAKEUP_STYLING, 'Makeup & Styling'),
        (ANCHORING, 'Anchoring / Emcee'),
        (OTHER, 'Other'),
    ]

    PER_PLATE = 'per_plate'
    PER_VENUE = 'per_venue'

    PRICING_TYPE_CHOICES = [
        (PER_PLATE, 'Per Plate'),
        (PER_VENUE, 'Per Venue'),
    ]

    vendor = models.ForeignKey(
        'services.Vendor', on_delete=models.CASCADE, related_name='outsourced_services',
    )
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    service_type = models.CharField(max_length=30, choices=SERVICE_TYPE_CHOICES, default=OTHER)
    pricing_type = models.CharField(max_length=20, choices=PRICING_TYPE_CHOICES, default=PER_PLATE)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    rating = models.DecimalField(
        max_digits=2, decimal_places=1, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        help_text='Out of 5',
    )
    times_opted = models.PositiveIntegerField(
        default=0, help_text='How many times this vendor has outsourced work to this service provider.',
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} ({self.get_service_type_display()})'

    @property
    def pricing_label(self):
        return 'Per Plate' if self.pricing_type == self.PER_PLATE else 'Per Venue'


class ServiceVendorBlockedDate(models.Model):
    """A date this outsourced service provider is NOT available.
    Every date not listed here is treated as available, shown on a simple
    calendar view (green = available, red = blocked).
    """
    service_vendor = models.ForeignKey(
        ServiceVendor, on_delete=models.CASCADE, related_name='blocked_dates',
    )
    date = models.DateField()
    note = models.CharField(max_length=200, blank=True)

    class Meta:
        unique_together = ('service_vendor', 'date')
        ordering = ['date']

    def __str__(self):
        return f'{self.service_vendor.name} — blocked {self.date}'


# ── Staff ────────────────────────────────────────────────────────────────

class StaffMember(models.Model):
    vendor = models.ForeignKey(
        'services.Vendor', on_delete=models.CASCADE, related_name='staff_members',
    )
    name = models.CharField(max_length=200)
    role = models.CharField(max_length=100, blank=True, help_text='e.g. Manager, Server, Coordinator')
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


# ── Gallery ──────────────────────────────────────────────────────────────

class GalleryPhoto(models.Model):
    vendor = models.ForeignKey(
        'services.Vendor', on_delete=models.CASCADE, related_name='gallery_photos',
    )
    name = models.CharField(max_length=200, help_text='Reference name for this photo')
    image = models.ImageField(upload_to='vendors/gallery/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f'{self.name} ({self.vendor.name})'