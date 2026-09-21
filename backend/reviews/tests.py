from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from services.models import (
    Category, City, Country, District, Service, State, Vendor,
)
from reviews.models import Review


def _make_service():
    country = Country.objects.create(
        name='India', code='IN', currency='INR',
        currency_symbol='₹', phone_code='+91',
    )
    state = State.objects.create(country=country, name='Maharashtra')
    district = District.objects.create(state=state, name='Pune District')
    city = City.objects.create(district=district, name='Pune')
    category = Category.objects.create(slug='banquet_hall')
    vendor = Vendor.objects.create(name='Test Vendor', phone='9999999999')
    service = Service.objects.create(
        vendor=vendor,
        category=category,
        city=city,
        name='Grand Hall',
        base_price=10000,
    )
    return service


class ReviewModelTest(TestCase):
    def setUp(self):
        self.service = _make_service()

    def test_default_status_is_pending(self):
        review = Review.objects.create(
            service=self.service, reviewer_name='Alice', rating=4, body='Great place!',
        )
        self.assertEqual(review.status, Review.STATUS_PENDING)

    def test_rating_below_1_fails_validation(self):
        review = Review(service=self.service, reviewer_name='Bob', rating=0, body='Bad')
        with self.assertRaises(ValidationError):
            review.full_clean()

    def test_rating_above_5_fails_validation(self):
        review = Review(service=self.service, reviewer_name='Bob', rating=6, body='Too good')
        with self.assertRaises(ValidationError):
            review.full_clean()

    def test_str_representation(self):
        review = Review.objects.create(
            service=self.service, reviewer_name='Carol', rating=5, body='Excellent!',
        )
        self.assertIn('Carol', str(review))
        self.assertIn('Grand Hall', str(review))


# ── Form tests ────────────────────────────────────────────────────────────────

class ReviewFormTest(TestCase):
    def test_valid_form(self):
        from reviews.forms import ReviewForm
        form = ReviewForm(data={
            'reviewer_name': 'Dave',
            'rating': '5',
            'body': 'Wonderful experience.',
        })
        self.assertTrue(form.is_valid())

    def test_blank_reviewer_name_invalid(self):
        from reviews.forms import ReviewForm
        form = ReviewForm(data={'reviewer_name': '', 'rating': '4', 'body': 'Nice'})
        self.assertFalse(form.is_valid())
        self.assertIn('reviewer_name', form.errors)

    def test_blank_body_invalid(self):
        from reviews.forms import ReviewForm
        form = ReviewForm(data={'reviewer_name': 'Eve', 'rating': '3', 'body': ''})
        self.assertFalse(form.is_valid())
        self.assertIn('body', form.errors)

    def test_rating_out_of_range_invalid(self):
        from reviews.forms import ReviewForm
        form = ReviewForm(data={'reviewer_name': 'Frank', 'rating': '6', 'body': 'OK'})
        self.assertFalse(form.is_valid())
        self.assertIn('rating', form.errors)


# ── View tests ────────────────────────────────────────────────────────────────

class AddReviewViewTest(TestCase):
    def setUp(self):
        self.service = _make_service()
        self.url = reverse('add_review', kwargs={'slug': self.service.slug})

    def test_post_creates_pending_review(self):
        response = self.client.post(self.url, {
            'reviewer_name': 'Grace',
            'rating': '4',
            'body': 'Really enjoyed it.',
        })
        self.assertRedirects(
            response,
            reverse('service_detail', kwargs={'slug': self.service.slug}),
            fetch_redirect_response=False,
        )
        review = Review.objects.get(reviewer_name='Grace')
        self.assertEqual(review.status, Review.STATUS_PENDING)
        self.assertEqual(review.service, self.service)

    def test_get_redirects_to_service_detail(self):
        response = self.client.get(self.url)
        self.assertRedirects(
            response,
            reverse('service_detail', kwargs={'slug': self.service.slug}),
            fetch_redirect_response=False,
        )

    def test_invalid_post_does_not_create_review(self):
        response = self.client.post(self.url, {
            'reviewer_name': '',
            'rating': '4',
            'body': 'Nice',
        })
        self.assertEqual(response.status_code, 302)  # redirect back on error too
        self.assertEqual(Review.objects.count(), 0)


# ── Admin action tests ────────────────────────────────────────────────────────

class ReviewAdminActionTest(TestCase):
    def setUp(self):
        from django.contrib.auth.models import User
        self.service = _make_service()
        self.superuser = User.objects.create_superuser(
            username='admin', password='pass', email='a@example.com'
        )
        self.client.login(username='admin', password='pass')
        self.r1 = Review.objects.create(
            service=self.service, reviewer_name='H', rating=4, body='Good',
        )
        self.r2 = Review.objects.create(
            service=self.service, reviewer_name='I', rating=2, body='Meh',
        )

    def test_bulk_approve_action(self):
        self.client.post(
            '/admin/reviews/review/',
            {
                'action': 'approve_selected',
                '_selected_action': [self.r1.pk, self.r2.pk],
            },
        )
        self.r1.refresh_from_db()
        self.r2.refresh_from_db()
        self.assertEqual(self.r1.status, Review.STATUS_APPROVED)
        self.assertEqual(self.r2.status, Review.STATUS_APPROVED)

    def test_bulk_reject_action(self):
        self.client.post(
            '/admin/reviews/review/',
            {
                'action': 'reject_selected',
                '_selected_action': [self.r1.pk, self.r2.pk],
            },
        )
        self.r1.refresh_from_db()
        self.r2.refresh_from_db()
        self.assertEqual(self.r1.status, Review.STATUS_REJECTED)
        self.assertEqual(self.r2.status, Review.STATUS_REJECTED)


# ── Service detail context tests ──────────────────────────────────────────────

class ServiceDetailContextTest(TestCase):
    def setUp(self):
        self.service = _make_service()

    def test_approved_reviews_in_context(self):
        Review.objects.create(
            service=self.service, reviewer_name='J', rating=5,
            body='Amazing!', status=Review.STATUS_APPROVED,
        )
        response = self.client.get(
            reverse('service_detail', kwargs={'slug': self.service.slug})
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('reviews', response.context)
        self.assertEqual(len(response.context['reviews']), 1)

    def test_pending_review_not_in_context(self):
        Review.objects.create(
            service=self.service, reviewer_name='K', rating=3,
            body='OK', status=Review.STATUS_PENDING,
        )
        response = self.client.get(
            reverse('service_detail', kwargs={'slug': self.service.slug})
        )
        self.assertEqual(len(response.context['reviews']), 0)

    def test_avg_rating_annotated_correctly(self):
        Review.objects.create(
            service=self.service, reviewer_name='L', rating=4,
            body='Good', status=Review.STATUS_APPROVED,
        )
        Review.objects.create(
            service=self.service, reviewer_name='M', rating=2,
            body='Meh', status=Review.STATUS_APPROVED,
        )
        response = self.client.get(
            reverse('service_detail', kwargs={'slug': self.service.slug})
        )
        self.assertAlmostEqual(float(response.context['service'].avg_rating), 3.0)

    def test_review_form_in_context(self):
        response = self.client.get(
            reverse('service_detail', kwargs={'slug': self.service.slug})
        )
        from reviews.forms import ReviewForm
        self.assertIsInstance(response.context['review_form'], ReviewForm)
