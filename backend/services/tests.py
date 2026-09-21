from decimal import Decimal

from django.test import TestCase, Client
from django.urls import reverse
from services.models import (
    Category, City, District, State, Country, Service, Vendor,
    DEFAULT_CANCELLATION_POLICY,
)


def _make_location():
    country = Country.objects.create(
        name='India', code='IN', currency='INR',
        currency_symbol='₹', phone_code='+91',
    )
    state = State.objects.create(country=country, name='Maharashtra')
    district = District.objects.create(state=state, name='Pune District')
    return district


class CategoryImageFieldTest(TestCase):
    def test_image_field_exists_and_is_blank_by_default(self):
        cat = Category(slug='banquet_hall', icon='bi-building')
        cat.save()
        self.assertTrue(hasattr(cat, 'image'))
        self.assertFalse(bool(cat.image))  # blank by default


class CityFeaturedFieldsTest(TestCase):
    def setUp(self):
        self.district = _make_location()

    def test_is_featured_defaults_to_false(self):
        city = City.objects.create(district=self.district, name='Pune')
        self.assertFalse(city.is_featured)

    def test_image_field_exists_and_is_blank_by_default(self):
        city = City.objects.create(district=self.district, name='Pune')
        self.assertFalse(bool(city.image))

    def test_featured_city_appears_in_filtered_queryset(self):
        City.objects.create(district=self.district, name='NotFeatured')
        featured = City.objects.create(
            district=self.district, name='Featured', is_featured=True,
        )
        qs = City.objects.filter(is_featured=True)
        self.assertIn(featured, qs)
        self.assertEqual(qs.count(), 1)


def _make_service(city, **overrides):
    category, _ = Category.objects.get_or_create(slug='banquet_hall')
    vendor = Vendor.objects.create(name='Test Vendor', phone='9999999999')
    defaults = {
        'vendor': vendor,
        'category': category,
        'city': city,
        'name': 'Test Hall',
        'base_price': Decimal('10000'),
    }
    defaults.update(overrides)
    return Service.objects.create(**defaults)


class ServicePricingTest(TestCase):
    """Our Price / Hall Owner Price split — see Service.effective_price and
    Service.final_price in services/models.py."""

    def setUp(self):
        self.city = City.objects.create(district=_make_location(), name='Pune')

    def test_effective_price_falls_back_to_base_price_when_our_price_unset(self):
        service = _make_service(self.city, base_price=Decimal('10000'))
        self.assertEqual(service.effective_price, Decimal('10000'))
        self.assertEqual(service.final_price, Decimal('10000.00'))

    def test_effective_price_uses_our_price_when_set(self):
        service = _make_service(
            self.city, base_price=Decimal('10000'), our_price=Decimal('12000'),
        )
        self.assertEqual(service.effective_price, Decimal('12000'))

    def test_final_price_applies_discount_to_our_price_not_base_price(self):
        service = _make_service(
            self.city,
            base_price=Decimal('10000'),
            our_price=Decimal('12000'),
            discount_percent=Decimal('10'),
        )
        self.assertEqual(service.final_price, Decimal('10800.00'))

    def test_final_price_with_no_discount_equals_effective_price(self):
        service = _make_service(self.city, our_price=Decimal('5000'))
        self.assertEqual(service.final_price, Decimal('5000.00'))


class ServiceCancellationPolicyTest(TestCase):
    def setUp(self):
        self.city = City.objects.create(district=_make_location(), name='Pune')

    def test_blank_policy_falls_back_to_default(self):
        service = _make_service(self.city)
        self.assertEqual(service.effective_cancellation_policy, DEFAULT_CANCELLATION_POLICY)

    def test_custom_policy_overrides_default(self):
        service = _make_service(self.city, cancellation_policy='No refunds, ever.')
        self.assertEqual(service.effective_cancellation_policy, 'No refunds, ever.')


class ServiceViewCountTest(TestCase):
    def setUp(self):
        self.city = City.objects.create(district=_make_location(), name='Pune')

    def test_view_count_defaults_to_zero(self):
        service = _make_service(self.city)
        self.assertEqual(service.view_count, 0)

    def test_service_detail_page_increments_view_count(self):
        service = _make_service(self.city)
        self.client.get(reverse('service_detail', args=[service.slug]))
        service.refresh_from_db()
        self.assertEqual(service.view_count, 1)
        self.client.get(reverse('service_detail', args=[service.slug]))
        service.refresh_from_db()
        self.assertEqual(service.view_count, 2)


class HomeViewContextTest(TestCase):
    def setUp(self):
        self.district = _make_location()

    def test_featured_cities_in_context(self):
        city = City.objects.create(
            district=self.district, name='Mumbai', is_featured=True,
        )
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('featured_cities', response.context)
        self.assertIn(city, response.context['featured_cities'])

    def test_non_featured_city_not_in_context(self):
        City.objects.create(district=self.district, name='Hidden')
        response = self.client.get(reverse('home'))
        self.assertEqual(response.context['featured_cities'].count(), 0)
