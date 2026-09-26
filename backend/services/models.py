from django.core.validators import RegexValidator
from django.db import models
from django.utils.text import slugify

DEFAULT_CANCELLATION_POLICY = (
    'Cancellations made more than 7 days before the event date receive a full refund. '
    'Cancellations made 3-7 days before the event receive a 50% refund. '
    'Cancellations made within 3 days of the event are non-refundable. '
    'Contact us directly for exceptional circumstances.'
)


# ── Location Hierarchy ────────────────────────────────────────────────────────

class Country(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=5, unique=True, help_text='ISO 2-letter code, e.g. IN')
    currency = models.CharField(max_length=10, default='INR', help_text='e.g. INR, USD')
    currency_symbol = models.CharField(max_length=5, default='₹')
    phone_code = models.CharField(max_length=10, default='+91')
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = 'Countries'
        ordering = ['name']

    def __str__(self):
        return self.name


class State(models.Model):
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='states')
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, blank=True, help_text='State/Province code')
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('country', 'name')
        ordering = ['name']

    def __str__(self):
        return f'{self.name}, {self.country.code}'


class District(models.Model):
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name='districts')
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('state', 'name')
        ordering = ['name']

    def __str__(self):
        return f'{self.name}, {self.state.name}'


class City(models.Model):
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name='cities')
    name = models.CharField(max_length=100)
    pin_code = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False, help_text='Show on home page city cards')
    image = models.ImageField(upload_to='cities/', blank=True)

    class Meta:
        unique_together = ('district', 'name')
        ordering = ['name']
        verbose_name_plural = 'Cities'

    def __str__(self):
        return f'{self.name} ({self.district.state.name})'

    @property
    def state(self):
        return self.district.state

    @property
    def country(self):
        return self.district.state.country

    @property
    def full_location(self):
        return f'{self.name}, {self.district.name}, {self.state.name}, {self.country.name}'


# ── Service Categories & Attributes ──────────────────────────────────────────

class Category(models.Model):
    BANQUET_HALL = 'banquet_hall'
    MUSIC_BAND = 'music_band'
    EVENT_MANAGEMENT = 'event_management'
    CATERING = 'catering'
    DANCING = 'dancing'
    PRIESTS = 'priests'
    HOTELS = 'hotels'

    CATEGORY_CHOICES = [
        (BANQUET_HALL, 'Banquet Hall'),
        (MUSIC_BAND, 'Music Band'),
        (EVENT_MANAGEMENT, 'Event Management'),
        (CATERING, 'Catering'),
        (DANCING, 'Dancing'),
        (PRIESTS, 'Priests'),
        (HOTELS, 'Hotels'),
    ]

    ICONS = {
        BANQUET_HALL: 'bi-building',
        MUSIC_BAND: 'bi-music-note-beamed',
        EVENT_MANAGEMENT: 'bi-calendar-event',
        CATERING: 'bi-cup-hot',
        DANCING: 'bi-person-arms-up',
        PRIESTS: 'bi-brightness-high',
        HOTELS: 'bi-house-door',
    }

    slug = models.SlugField(unique=True, choices=CATEGORY_CHOICES)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True, help_text='Uncheck to hide this category from the public site')
    image = models.ImageField(upload_to='categories/', blank=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['slug']

    def __str__(self):
        return self.get_slug_display()

    def save(self, *args, **kwargs):
        if not self.icon:
            self.icon = self.ICONS.get(self.slug, 'bi-star')
        super().save(*args, **kwargs)

    @property
    def display_name(self):
        return dict(self.CATEGORY_CHOICES).get(self.slug, self.slug)

    @property
    def static_image_url(self):
        """
        Path of a static image for this category, if one exists.

        Convention: drop a file named <slug>.png/.jpg/.jpeg/.webp into
        static/img/ (e.g. banquet_hall.png) and the home page category
        card picks it up automatically — no code change needed.
        Returns None when no such static file exists.
        """
        from django.contrib.staticfiles import finders
        for ext in ('.png', '.jpg', '.jpeg', '.webp'):
            rel = f'img/{self.slug}{ext}'
            if finders.find(rel):
                return rel
        return None

    def get_local_display_name(self, country=None, state=None):
        """Returns localized name for the given country/state, falls back to default."""
        if state:
            cfg = self.regional_configs.filter(country=country, state=state).first()
            if cfg and cfg.local_display_name:
                return cfg.local_display_name
        if country:
            cfg = self.regional_configs.filter(country=country, state=None).first()
            if cfg and cfg.local_display_name:
                return cfg.local_display_name
        return self.display_name

    def get_local_description(self, country=None, state=None):
        if state:
            cfg = self.regional_configs.filter(country=country, state=state).first()
            if cfg and cfg.local_description:
                return cfg.local_description
        if country:
            cfg = self.regional_configs.filter(country=country, state=None).first()
            if cfg and cfg.local_description:
                return cfg.local_description
        return self.description


class AttributeDefinition(models.Model):
    BOOLEAN = 'boolean'
    TEXT = 'text'
    NUMBER = 'number'
    CHOICE = 'choice'

    DATA_TYPE_CHOICES = [
        (BOOLEAN, 'Yes/No'),
        (TEXT, 'Text'),
        (NUMBER, 'Number'),
        (CHOICE, 'Choice'),
    ]

    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='attributes')
    name = models.CharField(max_length=100, help_text='Default English name')
    slug = models.SlugField(max_length=100)
    data_type = models.CharField(max_length=20, choices=DATA_TYPE_CHOICES, default=BOOLEAN)
    choices = models.TextField(blank=True, help_text='Comma-separated choices')
    unit = models.CharField(max_length=30, blank=True, help_text='e.g. persons, hours')
    is_filterable = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        unique_together = ('category', 'slug')
        ordering = ['order', 'name']

    def __str__(self):
        return f'{self.category} → {self.name}'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_choices_list(self):
        return [c.strip() for c in self.choices.split(',') if c.strip()]


class AttributeLocalName(models.Model):
    """Overrides an attribute's display name for a specific country or state."""
    attribute = models.ForeignKey(AttributeDefinition, on_delete=models.CASCADE, related_name='local_names')
    country = models.ForeignKey('Country', on_delete=models.CASCADE)
    state = models.ForeignKey('State', on_delete=models.SET_NULL, null=True, blank=True,
                               help_text='Leave blank for country-wide override')
    local_name = models.CharField(max_length=100, help_text='Name shown to users in this region')

    class Meta:
        unique_together = ('attribute', 'country', 'state')
        verbose_name = 'Attribute Local Name'

    def __str__(self):
        loc = self.state.name if self.state else self.country.name
        return f'{self.attribute.name} → "{self.local_name}" ({loc})'


class RegionalCategoryConfig(models.Model):
    """
    Defines region-specific display, attributes, and pricing for a category.
    State-level config overrides country-level config automatically.
    Leave state blank for a country-wide default.
    """
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='regional_configs')
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='category_configs')
    state = models.ForeignKey(State, on_delete=models.SET_NULL, null=True, blank=True,
                               related_name='category_configs',
                               help_text='Leave blank for country-wide default')

    # Local language label — overrides the default English category name in this region
    local_display_name = models.CharField(
        max_length=100, blank=True,
        help_text='Local name shown to users, e.g. "Purohit" instead of "Priests" in Telangana'
    )
    local_description = models.TextField(
        blank=True,
        help_text='Short description in the local language (shown on category cards/pages)'
    )

    enabled_attributes = models.ManyToManyField(
        AttributeDefinition, blank=True,
        help_text='Which attributes are shown/used for this category in this region'
    )
    price_unit_label = models.CharField(
        max_length=50, default='per event',
        help_text='Local label, e.g. "per event", "per night", "per plate"'
    )
    notes = models.TextField(blank=True, help_text='Admin-only notes')

    class Meta:
        unique_together = ('category', 'country', 'state')
        verbose_name = 'Regional Category Config'
        verbose_name_plural = 'Regional Category Configs'

    def __str__(self):
        loc = self.state.name if self.state else self.country.name
        label = self.local_display_name or self.category.display_name
        return f'{label} — {loc}'

    def get_display_name(self):
        return self.local_display_name or self.category.display_name

    def get_description(self):
        return self.local_description or self.category.description


# ── Vendors & Services ────────────────────────────────────────────────────────

class Vendor(models.Model):
    user = models.OneToOneField(
        'auth.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='vendor_profile',
        help_text='Link to a user account for vendor portal login.',
    )
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True, null=True, default=None)
    phone = models.CharField(max_length=20)
    address = models.TextField(blank=True)
    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, blank=True, related_name='vendors')
    avatar = models.ImageField(
        upload_to='vendors/avatars/', blank=True, null=True,
        verbose_name='Logo',
    )
    is_active = models.BooleanField(default=True)
    notify_on_booking = models.BooleanField(
        default=True,
        help_text='Send email to this vendor when a booking is received, confirmed, or cancelled.',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # ── Owner details ───────────────────────────────────────────────────
    # The person who owns/represents the business, for legal/verification
    # purposes. May differ from the day-to-day operational contact below.
    owner_name = models.CharField(max_length=200, blank=True)
    owner_email = models.EmailField(blank=True)
    owner_phone = models.CharField(max_length=20, blank=True)

    # ── Contact details ─────────────────────────────────────────────────
    # The person to reach for day-to-day operational matters (bookings,
    # coordination), which may be different from the owner above.
    contact_person_name = models.CharField(max_length=200, blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    contact_email = models.EmailField(blank=True)

    def __str__(self):
        return self.name


class HallDetails(models.Model):
    """Registration / legal details for the vendor's hall or venue."""
    vendor = models.OneToOneField(Vendor, on_delete=models.CASCADE, related_name='hall_details')
    hall_name = models.CharField(max_length=200, blank=True)
    business_registration_number = models.CharField(max_length=100, blank=True)
    gst_number = models.CharField(
        max_length=15, blank=True,
        verbose_name='GST',
        validators=[RegexValidator(
            regex=r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$',
            message='Enter a valid 15-character GST number (e.g. 22AAAAA0000A1Z5).',
        )],
        help_text='15-character GST Identification Number (GSTIN).',
    )
    trade_license_number = models.CharField(max_length=100, blank=True, verbose_name='Trade License')
    pan_number = models.CharField(
        max_length=10, blank=True,
        verbose_name='PAN Number',
        validators=[RegexValidator(
            regex=r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$',
            message='Enter a valid PAN number (e.g. ABCDE1234F).',
        )],
    )

    class Meta:
        verbose_name = 'Hall Details'
        verbose_name_plural = 'Hall Details'

    def __str__(self):
        return self.hall_name or f'Hall details for {self.vendor.name}'


class BankDetails(models.Model):
    """Bank account details used for vendor payouts."""
    ACCOUNT_TYPE_CHOICES = (
        ('savings', 'Savings'),
        ('current', 'Current'),
    )

    vendor = models.OneToOneField(Vendor, on_delete=models.CASCADE, related_name='bank_details')
    account_holder_name = models.CharField(max_length=200, blank=True)
    bank_name = models.CharField(max_length=200, blank=True)
    account_number = models.CharField(max_length=30, blank=True)
    ifsc_code = models.CharField(
        max_length=11, blank=True,
        verbose_name='IFSC Code',
        validators=[RegexValidator(
            regex=r'^[A-Z]{4}0[A-Z0-9]{6}$',
            message='Enter a valid 11-character IFSC code (e.g. SBIN0001234).',
        )],
    )
    branch_name = models.CharField(max_length=200, blank=True)
    account_type = models.CharField(
        max_length=10, choices=ACCOUNT_TYPE_CHOICES, blank=True, default='savings',
    )

    class Meta:
        verbose_name = 'Bank Details'
        verbose_name_plural = 'Bank Details'

    def __str__(self):
        return f'Bank details for {self.vendor.name}'


class VendorStaffUser(models.Model):
    """
    Additional vendor-portal logins beyond the owner (Vendor.user) — e.g.
    front-desk staff who manage bookings but can't touch pricing or photos.
    Vendor.user itself keeps meaning "the owner" unchanged.
    """
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='staff_users')
    user = models.OneToOneField('auth.User', on_delete=models.CASCADE, related_name='vendor_staff_profile')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.username} (staff @ {self.vendor.name})'


class Service(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='services')
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='services')
    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, blank=True, related_name='services')
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField(blank=True)
    address = models.TextField(blank=True)
    pin_code = models.CharField(max_length=20, blank=True)
    base_price = models.DecimalField(max_digits=12, decimal_places=2, default=0,
                                     help_text='Hall Owner Price — what the vendor charges. Not shown to customers.')
    our_price = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text='Our Price — the customer-facing price. Falls back to the Hall Owner Price if left blank.',
    )
    discount_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text='Discount % applied to Our Price for the final customer-facing price.',
    )
    price_unit = models.CharField(max_length=50, default='per event')
    cancellation_policy = models.TextField(
        blank=True,
        help_text='Shown to customers on the booking form. Leave blank to use the default policy.',
    )
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    view_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_featured', '-created_at']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)
            slug = base
            n = 1
            while Service.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base}-{n}'
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def currency_symbol(self):
        if self.city:
            return self.city.country.currency_symbol
        return '₹'

    @property
    def effective_price(self):
        return self.our_price if self.our_price is not None else self.base_price

    @property
    def final_price(self):
        price = self.effective_price
        if self.discount_percent:
            price = price * (1 - self.discount_percent / 100)
        return round(price, 2)

    @property
    def effective_cancellation_policy(self):
        return self.cancellation_policy or DEFAULT_CANCELLATION_POLICY

    @property
    def primary_image(self):
        return self.images.filter(is_primary=True).first() or self.images.first()

    def get_active_attributes(self):
        """Returns attribute definitions active for this service's region."""
        if not self.city:
            return self.category.attributes.all()
        state = self.city.state
        country = self.city.country
        config = (
            RegionalCategoryConfig.objects.filter(category=self.category, country=country, state=state).first()
            or RegionalCategoryConfig.objects.filter(category=self.category, country=country, state=None).first()
        )
        if config:
            return config.enabled_attributes.all()
        return self.category.attributes.all()


class ServiceAttributeValue(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='attribute_values')
    attribute = models.ForeignKey(AttributeDefinition, on_delete=models.CASCADE)
    value_boolean = models.BooleanField(null=True, blank=True)
    value_text = models.CharField(max_length=500, blank=True)
    value_number = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    class Meta:
        unique_together = ('service', 'attribute')

    def __str__(self):
        return f'{self.service.name} — {self.attribute.name}: {self.display_value}'

    @property
    def display_value(self):
        dtype = self.attribute.data_type
        if dtype == AttributeDefinition.BOOLEAN:
            return 'Yes' if self.value_boolean else 'No'
        if dtype == AttributeDefinition.NUMBER:
            val = self.value_number
            unit = self.attribute.unit
            if val is None:
                return '—'
            formatted_value = f'{val:.0f}' if val == val.to_integral_value() else str(val)
            return f'{formatted_value} {unit}'.strip()
        return self.value_text or '—'


class StaffProfile(models.Model):
    """
    Links a staff user to a location scope.
    Superusers ignore this and see everything.
    Priority: City > State > Country > (all data if all blank).
    """
    user = models.OneToOneField(
        'auth.User', on_delete=models.CASCADE, related_name='staff_profile'
    )
    country = models.ForeignKey(
        Country, on_delete=models.SET_NULL, null=True, blank=True,
        help_text='Limit access to this country'
    )
    state = models.ForeignKey(
        State, on_delete=models.SET_NULL, null=True, blank=True,
        help_text='Limit access to this state (overrides country)'
    )
    city = models.ForeignKey(
        City, on_delete=models.SET_NULL, null=True, blank=True,
        help_text='Limit access to this city (overrides state)'
    )
    notes = models.TextField(blank=True, help_text='Internal notes about this staff member')

    class Meta:
        verbose_name = 'Staff Profile'
        verbose_name_plural = 'Staff Profiles'

    def __str__(self):
        loc = self.city or self.state or self.country or 'All locations'
        return f'{self.user.username} — {loc}'

    @property
    def location_label(self):
        if self.city:
            return str(self.city.full_location)
        if self.state:
            return f'{self.state.name}, {self.state.country.name}'
        if self.country:
            return self.country.name
        return 'All locations'

    def filter_kwargs(self, city_path='city'):
        """
        Returns a dict of ORM filter kwargs scoped to this profile's location.
        city_path is the dotted path from the queryset model to its City FK.
        e.g. 'city' for Service/Vendor, 'service__city' for Booking/BlockedDate.
        """
        if self.city:
            return {city_path: self.city}
        if self.state:
            return {f'{city_path}__district__state': self.state}
        if self.country:
            return {f'{city_path}__district__state__country': self.country}
        return {}


class ServiceImage(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='services/')
    caption = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'{self.service.name} — image {self.order}'


# ── Home Page Hero Background ─────────────────────────────────────────────────

class HomeBackgroundImage(models.Model):
    """
    Images shown one-at-a-time in the home page hero slideshow.

    Managed entirely from the admin — uploading a new image here updates the
    live site immediately (no code change / redeploy needed), because the
    image is written to the configured media storage (local disk in
    development, Google Cloud Storage in production when GCS_MEDIA_BUCKET is
    set) rather than a static asset baked into the build.

    Only MAX_IMAGES are kept at a time. When a new image is uploaded past
    that limit, the oldest one is automatically deleted (file + record) so
    the admin never has to manually clean up.
    """
    MAX_IMAGES = 6

    image = models.ImageField(
        upload_to='home_background/',
        help_text=(
            f'Shown on the home page hero, one image at a time. '
            f'Up to {MAX_IMAGES} images are kept — uploading a new one beyond '
            f'that automatically removes the oldest. Wide landscape photos '
            f'(1600×900px or larger) work best.'
        ),
    )
    order = models.PositiveSmallIntegerField(
        default=0,
        help_text='Lower numbers play first in the slideshow. Images with the same order play oldest-first.',
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'uploaded_at']
        verbose_name = 'Home Background Image'
        verbose_name_plural = 'Home Background Images (max 6)'

    def __str__(self):
        return f'Home background #{self.pk} ({self.uploaded_at:%Y-%m-%d %H:%M})'

    @classmethod
    def enforce_limit(cls):
        """
        Delete the oldest image(s) beyond MAX_IMAGES, file included.
        Returns the number of images removed. Safe to call any time.
        """
        stale_ids = list(
            cls.objects.order_by('-uploaded_at').values_list('id', flat=True)[cls.MAX_IMAGES:]
        )
        if not stale_ids:
            return 0
        for obj in cls.objects.filter(id__in=stale_ids):
            obj.image.delete(save=False)
            obj.delete()
        return len(stale_ids)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        HomeBackgroundImage.enforce_limit()

    def delete(self, *args, **kwargs):
        self.image.delete(save=False)
        super().delete(*args, **kwargs)