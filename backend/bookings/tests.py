from django.contrib.auth.models import User
from django.test import TestCase

from services.models import City
from services.tests import _make_location, _make_service


class BookingAdminAddTest(TestCase):
    def setUp(self):
        User.objects.create_superuser('root', 'root@example.com', 'pw')
        self.client.login(username='root', password='pw')

    def test_add_form_renders(self):
        # Unsaved instance has total_amount=None and no pk; the readonly
        # balance/email-history fields must cope with that.
        resp = self.client.get('/admin/bookings/booking/add/')
        self.assertEqual(resp.status_code, 200)

    def test_add_booking_creates_it(self):
        city = City.objects.create(district=_make_location(), name='Pune')
        service = _make_service(city)
        resp = self.client.post('/admin/bookings/booking/add/', {
            'customer_name': 'Asha',
            'customer_email': 'asha@example.com',
            'customer_phone': '9999999999',
            'service': service.pk,
            'event_date': '2030-01-01',
            'guest_count': 10,
            'total_amount': '5000',
            'advance_amount': '1000',
            'status': 'pending',
            'terms_acceptances-TOTAL_FORMS': 0,
            'terms_acceptances-INITIAL_FORMS': 0,
        })
        self.assertEqual(resp.status_code, 302)
        from bookings.models import Booking
        self.assertEqual(Booking.objects.count(), 1)
