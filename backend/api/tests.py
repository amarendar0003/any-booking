from decimal import Decimal
from unittest.mock import patch

import jwt
from django.http import HttpResponse
from django.test import RequestFactory, TestCase, override_settings

from config.app_check import AppCheckMiddleware
from bookings.models import Booking
from services.models import (
    AttributeDefinition, Category, City, Country, District, ServiceAttributeValue,
    State, Service, Vendor,
)


def _make_location():
    country = Country.objects.create(
        name='India', code='IN', currency='INR',
        currency_symbol='₹', phone_code='+91',
    )
    state = State.objects.create(country=country, name='Telangana')
    district = District.objects.create(state=state, name='Hyderabad District')
    city = City.objects.create(district=district, name='Hyderabad')
    return country, state, city


def _make_service(city, **overrides):
    category, _ = Category.objects.get_or_create(slug='banquet_hall')
    vendor = Vendor.objects.create(name='Test Vendor', phone='9999999999')
    defaults = {
        'vendor': vendor,
        'category': category,
        'city': city,
        'name': 'Test Hall',
        'base_price': Decimal('10000'),
        'is_active': True,
    }
    defaults.update(overrides)
    return Service.objects.create(**defaults)


class AppCheckMiddlewareTests(TestCase):
    """config.app_check.AppCheckMiddleware, exercised through /api/categories/."""

    def test_noop_when_not_configured(self):
        # Default settings: FIREBASE_APP_CHECK_PROJECT_NUMBER unset, so
        # APP_CHECK_ENFORCED is False and no header is required.
        response = self.client.get('/api/categories/')
        self.assertEqual(response.status_code, 200)

    @override_settings(APP_CHECK_ENFORCED=True, FIREBASE_APP_CHECK_PROJECT_NUMBER='123456789')
    def test_rejects_missing_token_when_enforced(self):
        response = self.client.get('/api/categories/')
        self.assertEqual(response.status_code, 401)

    @override_settings(APP_CHECK_ENFORCED=True, FIREBASE_APP_CHECK_PROJECT_NUMBER='123456789')
    def test_rejects_invalid_token_when_enforced(self):
        with patch(
            'config.app_check.verify_app_check_token',
            side_effect=jwt.InvalidTokenError('bad signature'),
        ):
            response = self.client.get(
                '/api/categories/', HTTP_X_FIREBASE_APPCHECK='not-a-real-token'
            )
        self.assertEqual(response.status_code, 401)

    @override_settings(APP_CHECK_ENFORCED=True, FIREBASE_APP_CHECK_PROJECT_NUMBER='123456789')
    def test_allows_valid_token_when_enforced(self):
        with patch('config.app_check.verify_app_check_token', return_value={'sub': 'app:123'}):
            response = self.client.get(
                '/api/categories/', HTTP_X_FIREBASE_APPCHECK='a-valid-looking-token'
            )
        self.assertEqual(response.status_code, 200)

    @override_settings(APP_CHECK_ENFORCED=True, FIREBASE_APP_CHECK_PROJECT_NUMBER='123456789')
    def test_non_api_paths_are_never_gated(self):
        # Exercise the middleware directly so this doesn't depend on the
        # admin login template's static manifest being built.
        middleware = AppCheckMiddleware(lambda request: HttpResponse('ok'))
        request = RequestFactory().get('/admin/login/')
        response = middleware(request)
        self.assertEqual(response.status_code, 200)


class LocationListViewTest(TestCase):
    def setUp(self):
        self.country, self.state, self.city = _make_location()

    def test_countries_list(self):
        response = self.client.get('/api/countries/')
        self.assertEqual(response.status_code, 200)
        names = [c['name'] for c in response.json()['results']]
        self.assertIn('India', names)

    def test_states_filtered_by_country(self):
        other_country = Country.objects.create(
            name='USA', code='US', currency='USD', currency_symbol='$', phone_code='+1',
        )
        State.objects.create(country=other_country, name='California')

        response = self.client.get('/api/states/', {'country': self.country.id})
        self.assertEqual(response.status_code, 200)
        names = [s['name'] for s in response.json()['results']]
        self.assertEqual(names, ['Telangana'])

    def test_states_without_country_param_returns_all(self):
        response = self.client.get('/api/states/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['count'], 1)


class ServiceListFilterTest(TestCase):
    def setUp(self):
        self.country, self.state, self.city = _make_location()

    def test_price_and_discount_fields_are_serialized(self):
        _make_service(
            self.city,
            base_price=Decimal('10000'),
            our_price=Decimal('12000'),
            discount_percent=Decimal('10'),
        )
        response = self.client.get('/api/services/')
        result = response.json()['results'][0]
        self.assertEqual(result['price'], '10800.00')
        self.assertEqual(result['original_price'], '12000.00')
        self.assertEqual(result['discount_percent'], '10.00')
        self.assertNotIn('base_price', result)  # hall owner price is never public

    def test_filter_by_country(self):
        _make_service(self.city, name='In Scope')
        other_country = Country.objects.create(
            name='USA', code='US', currency='USD', currency_symbol='$', phone_code='+1',
        )
        other_state = State.objects.create(country=other_country, name='California')
        other_district = District.objects.create(state=other_state, name='LA District')
        other_city = City.objects.create(district=other_district, name='LA')
        _make_service(other_city, name='Out Of Scope')

        response = self.client.get('/api/services/', {'country': self.country.id})
        names = [r['name'] for r in response.json()['results']]
        self.assertEqual(names, ['In Scope'])

    def test_filter_by_state(self):
        _make_service(self.city, name='In State')
        response = self.client.get('/api/services/', {'state': self.state.id})
        names = [r['name'] for r in response.json()['results']]
        self.assertEqual(names, ['In State'])

        wrong_state = State.objects.create(country=self.country, name='Kerala')
        response = self.client.get('/api/services/', {'state': wrong_state.id})
        self.assertEqual(response.json()['count'], 0)

    def test_filter_by_parking(self):
        with_parking = _make_service(self.city, name='Has Parking')
        _make_service(self.city, name='No Parking')
        attr = AttributeDefinition.objects.create(
            category=with_parking.category, name='Parking Available',
            slug='parking-available', data_type=AttributeDefinition.BOOLEAN,
        )
        ServiceAttributeValue.objects.create(
            service=with_parking, attribute=attr, value_boolean=True,
        )

        response = self.client.get('/api/services/', {'parking': '1'})
        names = [r['name'] for r in response.json()['results']]
        self.assertEqual(names, ['Has Parking'])

    def test_price_ordering_uses_effective_discounted_price_not_base_price(self):
        # Cheap on paper (base_price) but expensive after our_price/discount —
        # ordering must reflect the real customer-facing price, not base_price.
        _make_service(
            self.city, name='Looks Cheap', base_price=Decimal('100'),
            our_price=Decimal('50000'),
        )
        _make_service(
            self.city, name='Looks Expensive', base_price=Decimal('50000'),
            our_price=Decimal('100'),
        )

        response = self.client.get('/api/services/', {'ordering': 'price_asc'})
        names = [r['name'] for r in response.json()['results']]
        self.assertEqual(names, ['Looks Expensive', 'Looks Cheap'])


class CategoryListViewTest(TestCase):
    def test_listing_count_counts_only_active_services(self):
        _, _, city = _make_location()
        _make_service(city, name='Active Hall')
        _make_service(city, name='Hidden Hall', is_active=False)
        response = self.client.get('/api/categories/')
        self.assertEqual(response.status_code, 200)
        banquet = next(c for c in response.json()['results'] if c['slug'] == 'banquet_hall')
        self.assertEqual(banquet['listing_count'], 1)


    def test_listing_count_respects_country_and_state(self):
        country, state, city = _make_location()
        _make_service(city)
        response = self.client.get(f'/api/categories/?country={country.id}&state={state.id}')
        banquet = next(c for c in response.json()['results'] if c['slug'] == 'banquet_hall')
        self.assertEqual(banquet['listing_count'], 1)
        response = self.client.get(f'/api/categories/?country={country.id + 999}')
        banquet = next(c for c in response.json()['results'] if c['slug'] == 'banquet_hall')
        self.assertEqual(banquet['listing_count'], 0)


class LocationMatchViewTest(TestCase):
    def test_matches_country_and_fuzzy_state(self):
        country, state, _ = _make_location()
        response = self.client.get(
            f'/api/locations/match/?country_code={country.code.lower()}&state_name=telangana'
        )
        data = response.json()
        self.assertEqual(data['country_id'], country.id)
        self.assertEqual(data['state_id'], state.id)

    def test_unknown_country_returns_nulls(self):
        response = self.client.get('/api/locations/match/?country_code=ZZ&state_name=Nowhere')
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()['country_id'])


class ServiceDetailViewTest(TestCase):
    def setUp(self):
        _, _, self.city = _make_location()

    def test_view_count_increments_on_detail_fetch(self):
        service = _make_service(self.city)
        self.client.get(f'/api/services/{service.slug}/')
        service.refresh_from_db()
        self.assertEqual(service.view_count, 1)


class BookingCreateDailyLimitTest(TestCase):
    def setUp(self):
        _, _, self.city = _make_location()
        self.service = _make_service(self.city)

    def _post(self, phone, event_date, **overrides):
        payload = {
            'service_slug': self.service.slug,
            'customer_name': 'Alice',
            'customer_phone': phone,
            'event_date': event_date,
            'total_amount': '1000',
            'terms_accepted': True,
        }
        payload.update(overrides)
        return self.client.post('/api/bookings/', payload)

    def test_first_booking_of_the_day_succeeds(self):
        response = self._post('9998887777', '2027-01-01')
        self.assertEqual(response.status_code, 201)

    def test_second_booking_same_phone_same_day_is_rejected(self):
        self._post('9998887777', '2027-01-01')
        response = self._post('9998887777', '2027-06-06')  # different event date
        self.assertEqual(response.status_code, 400)
        self.assertIn('customer_phone', response.json())

    def test_different_phone_same_day_is_allowed(self):
        self._post('9998887777', '2027-01-01')
        response = self._post('1112223333', '2027-01-01')
        self.assertEqual(response.status_code, 201)

    def test_booking_without_email_is_allowed(self):
        response = self._post('9998887777', '2027-01-01')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Booking.objects.get().customer_email, '')
