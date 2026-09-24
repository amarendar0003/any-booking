from decimal import Decimal

from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import User
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from bookings.models import Booking, EmailLog
from services.models import Category, City, Country, District, Service, State, Vendor, VendorStaffUser


def _make_city():
    country = Country.objects.create(
        name='India', code='IN', currency='INR',
        currency_symbol='₹', phone_code='+91',
    )
    state = State.objects.create(country=country, name='Maharashtra')
    district = District.objects.create(state=state, name='Pune District')
    return City.objects.create(district=district, name='Pune')


def _make_vendor_with_service(city, name='Test Vendor', phone='9999999999'):
    category, _ = Category.objects.get_or_create(slug='banquet_hall')
    vendor = Vendor.objects.create(name=name, phone=phone, email=f'{name.lower().replace(" ", "")}@example.com')
    service = Service.objects.create(
        vendor=vendor,
        category=category,
        city=city,
        name=f'{name} Hall',
        base_price=10000,
    )
    return vendor, service


def _make_booking(service, status=Booking.STATUS_PENDING):
    return Booking.objects.create(
        service=service,
        customer_name='Alice',
        customer_email='alice@example.com',
        customer_phone='8888888888',
        event_date='2026-12-01',
        total_amount=10000,
        status=status,
    )


class VendorApproveBookingTest(TestCase):
    def setUp(self):
        city = _make_city()
        self.vendor, self.service = _make_vendor_with_service(city)
        self.user = User.objects.create_user(username='vendor1', password='pass1234')
        self.vendor.user = self.user
        self.vendor.save(update_fields=['user'])

        self.other_vendor, self.other_service = _make_vendor_with_service(
            city, name='Other Vendor', phone='7777777777',
        )
        self.other_user = User.objects.create_user(username='vendor2', password='pass1234')
        self.other_vendor.user = self.other_user
        self.other_vendor.save(update_fields=['user'])

    def test_approve_pending_booking_confirms_and_notifies(self):
        booking = _make_booking(self.service)
        self.client.login(username='vendor1', password='pass1234')
        mail.outbox.clear()

        response = self.client.post(reverse('vendor_approve_booking', args=[booking.id]))

        booking.refresh_from_db()
        self.assertRedirects(response, reverse('vendor_bookings'))
        self.assertEqual(booking.status, Booking.STATUS_CONFIRMED)
        self.assertEqual(len(mail.outbox), 2)  # customer + vendor notify
        self.assertTrue(
            EmailLog.objects.filter(booking=booking, email_type=EmailLog.TYPE_APPROVED).exists()
        )

    def test_cannot_approve_another_vendors_booking(self):
        booking = _make_booking(self.service)
        self.client.login(username='vendor2', password='pass1234')

        response = self.client.post(reverse('vendor_approve_booking', args=[booking.id]))

        booking.refresh_from_db()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(booking.status, Booking.STATUS_PENDING)

    def test_approving_non_pending_booking_is_a_no_op(self):
        booking = _make_booking(self.service, status=Booking.STATUS_CONFIRMED)
        self.client.login(username='vendor1', password='pass1234')
        mail.outbox.clear()

        response = self.client.post(reverse('vendor_approve_booking', args=[booking.id]))

        booking.refresh_from_db()
        self.assertRedirects(response, reverse('vendor_bookings'))
        self.assertEqual(booking.status, Booking.STATUS_CONFIRMED)
        self.assertEqual(len(mail.outbox), 0)

    def test_approve_requires_login(self):
        booking = _make_booking(self.service)

        response = self.client.post(reverse('vendor_approve_booking', args=[booking.id]))

        booking.refresh_from_db()
        self.assertRedirects(response, '/')
        self.assertEqual(booking.status, Booking.STATUS_PENDING)

    def test_approve_requires_post(self):
        booking = _make_booking(self.service)
        self.client.login(username='vendor1', password='pass1234')

        response = self.client.get(reverse('vendor_approve_booking', args=[booking.id]))

        self.assertEqual(response.status_code, 405)


class VendorRolePermissionsTest(TestCase):
    """Owner (Vendor.user) vs staff (VendorStaffUser) — see
    vendors/views.py:_resolve_vendor_role and owner_required."""

    def setUp(self):
        city = _make_city()
        self.vendor, self.service = _make_vendor_with_service(city)

        self.owner_user = User.objects.create_user(username='owner1', password='pass1234')
        self.vendor.user = self.owner_user
        self.vendor.save(update_fields=['user'])

        self.staff_user = User.objects.create_user(username='staff1', password='pass1234')
        VendorStaffUser.objects.create(vendor=self.vendor, user=self.staff_user)

    def test_owner_can_view_edit_service_page(self):
        self.client.login(username='owner1', password='pass1234')
        response = self.client.get(reverse('vendor_edit_service', args=[self.service.id]))
        self.assertEqual(response.status_code, 200)

    def test_owner_can_update_price(self):
        self.client.login(username='owner1', password='pass1234')
        response = self.client.post(
            reverse('vendor_edit_service', args=[self.service.id]),
            {'base_price': '15000', 'price_unit': 'per day'},
        )
        self.assertEqual(response.status_code, 302)
        self.service.refresh_from_db()
        self.assertEqual(self.service.base_price, Decimal('15000'))
        self.assertEqual(self.service.price_unit, 'per day')

    def test_staff_cannot_view_edit_service_page(self):
        self.client.login(username='staff1', password='pass1234')
        response = self.client.get(
            reverse('vendor_edit_service', args=[self.service.id]), follow=True,
        )
        self.assertRedirects(response, reverse('vendor_dashboard'))

    def test_staff_post_does_not_change_price(self):
        self.client.login(username='staff1', password='pass1234')
        self.client.post(
            reverse('vendor_edit_service', args=[self.service.id]),
            {'base_price': '99999', 'price_unit': 'per day'},
        )
        self.service.refresh_from_db()
        self.assertEqual(self.service.base_price, Decimal('10000'))  # unchanged

    def test_staff_can_view_dashboard(self):
        self.client.login(username='staff1', password='pass1234')
        response = self.client.get(reverse('vendor_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_staff_can_view_bookings(self):
        self.client.login(username='staff1', password='pass1234')
        response = self.client.get(reverse('vendor_bookings'))
        self.assertEqual(response.status_code, 200)

    def test_staff_can_approve_booking(self):
        booking = _make_booking(self.service)
        self.client.login(username='staff1', password='pass1234')
        response = self.client.post(reverse('vendor_approve_booking', args=[booking.id]))
        booking.refresh_from_db()
        self.assertRedirects(response, reverse('vendor_bookings'))
        self.assertEqual(booking.status, Booking.STATUS_CONFIRMED)

    def test_account_with_no_vendor_link_is_rejected(self):
        User.objects.create_user(username='rando', password='pass1234')
        self.client.login(username='rando', password='pass1234')
        response = self.client.get(reverse('vendor_dashboard'))
        self.assertRedirects(response, '/')


class VendorEditServicePhotosTest(TestCase):
    def setUp(self):
        city = _make_city()
        self.vendor, self.service = _make_vendor_with_service(city)
        self.owner_user = User.objects.create_user(username='owner1', password='pass1234')
        self.vendor.user = self.owner_user
        self.vendor.save(update_fields=['user'])
        self.client.login(username='owner1', password='pass1234')

    def _tiny_image(self, name='photo.png'):
        return SimpleUploadedFile(name, b'\x89PNG\r\n\x1a\n' + b'0' * 20, content_type='image/png')

    def test_upload_adds_an_image(self):
        self.client.post(
            reverse('vendor_edit_service', args=[self.service.id]),
            {'base_price': '10000', 'price_unit': 'per event', 'new_image': self._tiny_image()},
        )
        self.assertEqual(self.service.images.count(), 1)

    def test_set_primary_image(self):
        self.client.post(
            reverse('vendor_edit_service', args=[self.service.id]),
            {'base_price': '10000', 'price_unit': 'per event', 'new_image': self._tiny_image('a.png')},
        )
        self.client.post(
            reverse('vendor_edit_service', args=[self.service.id]),
            {'base_price': '10000', 'price_unit': 'per event', 'new_image': self._tiny_image('b.png')},
        )
        first_image = self.service.images.order_by('id').first()
        self.client.post(
            reverse('vendor_edit_service', args=[self.service.id]),
            {'base_price': '10000', 'price_unit': 'per event', 'primary_image': str(first_image.id)},
        )
        first_image.refresh_from_db()
        self.assertTrue(first_image.is_primary)
        self.assertEqual(self.service.images.filter(is_primary=True).count(), 1)

    def test_delete_image(self):
        self.client.post(
            reverse('vendor_edit_service', args=[self.service.id]),
            {'base_price': '10000', 'price_unit': 'per event', 'new_image': self._tiny_image()},
        )
        image = self.service.images.first()
        self.client.post(
            reverse('vendor_edit_service', args=[self.service.id]),
            {'base_price': '10000', 'price_unit': 'per event', 'delete_image': [str(image.id)]},
        )
        self.assertEqual(self.service.images.count(), 0)


class VendorCancelBookingTest(TestCase):
    def setUp(self):
        city = _make_city()
        self.vendor, self.service = _make_vendor_with_service(city)
        self.staff_user = User.objects.create_user(username='staff1', password='pass1234')
        VendorStaffUser.objects.create(vendor=self.vendor, user=self.staff_user)
        self.client.login(username='staff1', password='pass1234')

    def test_cancel_with_refund_updates_booking_and_logs_and_notifies(self):
        booking = _make_booking(self.service, status=Booking.STATUS_CONFIRMED)
        mail.outbox.clear()

        response = self.client.post(
            reverse('vendor_cancel_booking', args=[booking.id]),
            {'refund_type': Booking.REFUND_PARTIAL, 'refund_amount': '500', 'cancellation_reason': 'Change of plans'},
        )

        booking.refresh_from_db()
        self.assertRedirects(response, reverse('vendor_bookings'))
        self.assertEqual(booking.status, Booking.STATUS_CANCELLED)
        self.assertEqual(booking.refund_type, Booking.REFUND_PARTIAL)
        self.assertEqual(float(booking.refund_amount), 500.0)
        self.assertEqual(booking.cancellation_reason, 'Change of plans')
        self.assertTrue(len(mail.outbox) >= 1)
        self.assertTrue(
            LogEntry.objects.filter(
                object_id=str(booking.pk), user=self.staff_user,
            ).exists()
        )

    def test_cannot_cancel_a_completed_booking(self):
        booking = _make_booking(self.service, status=Booking.STATUS_COMPLETED)
        self.client.post(
            reverse('vendor_cancel_booking', args=[booking.id]),
            {'refund_type': Booking.REFUND_NONE},
        )
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.STATUS_COMPLETED)

    def test_cannot_cancel_another_vendors_booking(self):
        other_vendor, other_service = _make_vendor_with_service(
            self.service.city, name='Other Vendor', phone='6666666666',
        )
        booking = _make_booking(other_service)
        response = self.client.post(
            reverse('vendor_cancel_booking', args=[booking.id]),
            {'refund_type': Booking.REFUND_NONE},
        )
        self.assertEqual(response.status_code, 404)
