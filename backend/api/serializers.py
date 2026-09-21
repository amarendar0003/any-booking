from django.utils import timezone
from rest_framework import serializers
from services.models import (
    Country, State, City, Category, Vendor, Service,
    ServiceImage, ServiceAttributeValue, AttributeDefinition,
)
from bookings.models import Booking
from reviews.models import Review


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ['id', 'name', 'code', 'currency', 'currency_symbol', 'phone_code']


class StateSerializer(serializers.ModelSerializer):
    country_id = serializers.IntegerField(source='country.id', read_only=True)

    class Meta:
        model = State
        fields = ['id', 'name', 'code', 'country_id']


class CitySerializer(serializers.ModelSerializer):
    state_name = serializers.CharField(source='district.state.name', read_only=True)
    country_name = serializers.CharField(source='district.state.country.name', read_only=True)
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = City
        fields = ['id', 'name', 'is_featured', 'state_name', 'country_name', 'image_url']

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return None


class CategorySerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()
    listing_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Category
        fields = ['id', 'slug', 'display_name', 'icon', 'description', 'listing_count']

    def get_display_name(self, obj):
        return obj.get_local_display_name()


class AttributeValueSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='attribute.name')
    slug = serializers.CharField(source='attribute.slug')
    display_value = serializers.CharField()

    class Meta:
        model = ServiceAttributeValue
        fields = ['name', 'slug', 'display_value']


class ServiceImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = ServiceImage
        fields = ['id', 'url', 'caption', 'is_primary', 'order']

    def get_url(self, obj):
        request = self.context.get('request')
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return None


class VendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = ['id', 'name', 'phone', 'email']


class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ['id', 'reviewer_name', 'rating', 'body', 'created_at']


class ServiceListSerializer(serializers.ModelSerializer):
    """Compact serializer for list views."""
    category_slug = serializers.CharField(source='category.slug')
    category_name = serializers.SerializerMethodField()
    city_name = serializers.CharField(source='city.name', default=None)
    vendor_name = serializers.CharField(source='vendor.name', default='')
    primary_image_url = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    attributes = AttributeValueSerializer(source='attribute_values', many=True)
    price = serializers.DecimalField(source='final_price', max_digits=12, decimal_places=2, read_only=True)
    original_price = serializers.DecimalField(source='effective_price', max_digits=12, decimal_places=2, read_only=True)
    cancellation_policy = serializers.CharField(source='effective_cancellation_policy', read_only=True)

    class Meta:
        model = Service
        fields = [
            'id', 'name', 'slug', 'category_slug', 'category_name',
            'city_name', 'vendor_name', 'price', 'original_price', 'discount_percent', 'price_unit',
            'is_featured', 'primary_image_url', 'average_rating', 'review_count',
            'attributes', 'cancellation_policy',
        ]

    def get_category_name(self, obj):
        return obj.category.get_local_display_name()

    def get_primary_image_url(self, obj):
        request = self.context.get('request')
        img = obj.primary_image
        if img and request:
            return request.build_absolute_uri(img.image.url)
        return None

    def get_average_rating(self, obj):
        reviews = obj.reviews.filter(status='approved')
        if not reviews.exists():
            return None
        return round(sum(r.rating for r in reviews) / reviews.count(), 1)

    def get_review_count(self, obj):
        return obj.reviews.filter(status='approved').count()


class ServiceDetailSerializer(serializers.ModelSerializer):
    """Full serializer for detail view."""
    category = CategorySerializer()
    city = CitySerializer()
    vendor = VendorSerializer()
    images = ServiceImageSerializer(many=True)
    attributes = AttributeValueSerializer(source='attribute_values', many=True)
    reviews = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    booked_dates = serializers.SerializerMethodField()
    price = serializers.DecimalField(source='final_price', max_digits=12, decimal_places=2, read_only=True)
    original_price = serializers.DecimalField(source='effective_price', max_digits=12, decimal_places=2, read_only=True)
    cancellation_policy = serializers.CharField(source='effective_cancellation_policy', read_only=True)

    class Meta:
        model = Service
        fields = [
            'id', 'name', 'slug', 'category', 'city', 'vendor',
            'description', 'address', 'price', 'original_price', 'discount_percent', 'price_unit',
            'is_featured', 'images', 'attributes', 'reviews',
            'average_rating', 'review_count', 'booked_dates', 'cancellation_policy',
        ]

    def get_reviews(self, obj):
        approved = obj.reviews.filter(status='approved').order_by('-created_at')
        return ReviewSerializer(approved, many=True).data

    def get_average_rating(self, obj):
        reviews = obj.reviews.filter(status='approved')
        if not reviews.exists():
            return None
        return round(sum(r.rating for r in reviews) / reviews.count(), 1)

    def get_review_count(self, obj):
        return obj.reviews.filter(status='approved').count()

    def get_booked_dates(self, obj):
        confirmed = obj.bookings.filter(
            status__in=['pending', 'confirmed']
        ).values_list('event_date', flat=True)
        blocked = obj.blocked_dates.values_list('date', flat=True)
        dates = sorted(set(list(confirmed) + list(blocked)))
        return [d.isoformat() for d in dates]


class BookingCreateSerializer(serializers.ModelSerializer):
    service_slug = serializers.SlugField(write_only=True)
    terms_accepted = serializers.BooleanField(write_only=True)

    class Meta:
        model = Booking
        fields = [
            'service_slug', 'customer_name', 'customer_email', 'customer_phone',
            'event_date', 'guest_count', 'special_requests',
            'total_amount', 'terms_accepted',
        ]

    def validate_service_slug(self, value):
        try:
            return Service.objects.get(slug=value, is_active=True)
        except Service.DoesNotExist:
            raise serializers.ValidationError('Service not found.')

    def validate(self, data):
        if not data.get('terms_accepted'):
            raise serializers.ValidationError({'terms_accepted': 'You must accept the terms.'})

        phone = data.get('customer_phone', '')
        if phone and Booking.objects.filter(
            customer_phone=phone, created_at__date=timezone.localdate()
        ).exists():
            raise serializers.ValidationError({
                'customer_phone': 'Only one booking per day is allowed per phone number. '
                                   'Please contact us directly if you need to make another booking today.',
            })
        return data

    def create(self, validated_data):
        service = validated_data.pop('service_slug')
        validated_data.pop('terms_accepted')
        return Booking.objects.create(service=service, **validated_data)


class BookingDetailSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source='service.name')
    service_slug = serializers.CharField(source='service.slug')
    category_slug = serializers.CharField(source='service.category.slug')

    class Meta:
        model = Booking
        fields = [
            'id', 'confirmation_number', 'service_name', 'service_slug',
            'category_slug', 'customer_name', 'customer_email', 'customer_phone',
            'event_date', 'guest_count', 'special_requests',
            'total_amount', 'advance_amount', 'status',
            'cancellation_requested', 'created_at',
        ]


class CancellationRequestSerializer(serializers.Serializer):
    reason = serializers.CharField(min_length=10)
