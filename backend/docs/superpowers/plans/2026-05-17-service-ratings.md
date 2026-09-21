# Service Ratings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow any visitor to submit a star rating + review for a service listing; pending reviews are approved by admin before appearing publicly; average rating shows on listing cards.

**Architecture:** A new `reviews` Django app owns the `Review` model, form, view, and admin. The existing `service_detail` view is extended to pass approved reviews and a blank form to the template. Average rating is computed via `Avg` annotation — no denormalised field.

**Tech Stack:** Django 5.2, PostgreSQL, Bootstrap 5 + Bootstrap Icons, Django admin bulk actions.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `reviews/__init__.py` | Create | App package |
| `reviews/models.py` | Create | `Review` model |
| `reviews/forms.py` | Create | `ReviewForm` |
| `reviews/views.py` | Create | `add_review` POST-only view |
| `reviews/urls.py` | Create | URL pattern for submission |
| `reviews/admin.py` | Create | `ReviewAdmin` with bulk approve/reject |
| `reviews/tests.py` | Create | All tests for this feature |
| `reviews/migrations/0001_initial.py` | Auto-generated | DB migration |
| `config/settings.py` | Modify | Add `'reviews'` to `INSTALLED_APPS` |
| `config/urls.py` | Modify | Include `reviews.urls` |
| `services/views.py` | Modify | Annotate `service_detail` with `avg_rating`; add `reviews` + `review_form` to context |
| `templates/services/detail.html` | Modify | Reviews section + submission form |
| `templates/partials/service_card.html` | Modify | Average star badge |

---

## Task 1: `Review` model + migration

**Files:**
- Create: `reviews/__init__.py`
- Create: `reviews/models.py`
- Create: `reviews/tests.py` (model tests only for now)
- Modify: `config/settings.py`

- [ ] **Step 1: Create the app package**

```bash
mkdir -p reviews/migrations
touch reviews/__init__.py reviews/migrations/__init__.py
```

- [ ] **Step 2: Write `reviews/models.py`**

```python
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from services.models import Service


class Review(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='reviews')
    reviewer_name = models.CharField(max_length=100)
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    body = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.reviewer_name} – {self.service.name} ({self.rating}★)'
```

- [ ] **Step 3: Add `reviews` to `INSTALLED_APPS` in `config/settings.py`**

Find the `INSTALLED_APPS` list and add `'reviews'` after `'terms'`:

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'services',
    'bookings',
    'vendors',
    'payments',
    'terms',
    'reviews',
]
```

- [ ] **Step 4: Write the failing model tests in `reviews/tests.py`**

```python
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from services.models import (
    Category, City, Country, District, Service, State, Vendor,
)
from reviews.models import Review


# ── Shared fixture helpers ────────────────────────────────────────────────────

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


# ── Model tests ───────────────────────────────────────────────────────────────

class ReviewModelTest(TestCase):
    def setUp(self):
        self.service = _make_service()

    def test_default_status_is_pending(self):
        review = Review.objects.create(
            service=self.service,
            reviewer_name='Alice',
            rating=4,
            body='Great place!',
        )
        self.assertEqual(review.status, Review.STATUS_PENDING)

    def test_rating_below_1_fails_validation(self):
        review = Review(
            service=self.service,
            reviewer_name='Bob',
            rating=0,
            body='Bad',
        )
        with self.assertRaises(ValidationError):
            review.full_clean()

    def test_rating_above_5_fails_validation(self):
        review = Review(
            service=self.service,
            reviewer_name='Bob',
            rating=6,
            body='Too good',
        )
        with self.assertRaises(ValidationError):
            review.full_clean()

    def test_str_representation(self):
        review = Review.objects.create(
            service=self.service,
            reviewer_name='Carol',
            rating=5,
            body='Excellent!',
        )
        self.assertIn('Carol', str(review))
        self.assertIn('Grand Hall', str(review))
```

- [ ] **Step 5: Run tests — expect failure (app not migrated yet)**

```bash
python manage.py test reviews.tests.ReviewModelTest --verbosity=2
```

Expected: `django.db.utils.ProgrammingError` or migration error — the table doesn't exist yet.

- [ ] **Step 6: Generate and apply the migration**

```bash
python manage.py makemigrations reviews
python manage.py migrate
```

Expected output includes: `Creating tables... reviews_review`

- [ ] **Step 7: Run model tests — expect pass**

```bash
python manage.py test reviews.tests.ReviewModelTest --verbosity=2
```

Expected: `4 tests, 0 failures`

- [ ] **Step 8: Commit**

```bash
git add reviews/ config/settings.py
git commit -m "Add reviews app with Review model and migration"
```

---

## Task 2: `ReviewForm` + `add_review` view + URL

**Files:**
- Create: `reviews/forms.py`
- Create: `reviews/views.py`
- Create: `reviews/urls.py`
- Modify: `config/urls.py`
- Modify: `reviews/tests.py` (add form + view tests)

- [ ] **Step 1: Add form and view tests to `reviews/tests.py`**

Append these classes to the existing file:

```python
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
```

- [ ] **Step 2: Run tests — expect failure**

```bash
python manage.py test reviews.tests.ReviewFormTest reviews.tests.AddReviewViewTest --verbosity=2
```

Expected: `ImportError` — `reviews.forms` and `reviews.views` don't exist yet.

- [ ] **Step 3: Write `reviews/forms.py`**

```python
from django import forms
from .models import Review


class ReviewForm(forms.ModelForm):
    rating = forms.IntegerField(
        min_value=1,
        max_value=5,
        widget=forms.NumberInput(attrs={'min': 1, 'max': 5}),
    )

    class Meta:
        model = Review
        fields = ['reviewer_name', 'rating', 'body']
        widgets = {
            'reviewer_name': forms.TextInput(attrs={'placeholder': 'Your name'}),
            'body': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Share your experience…'}),
        }
        labels = {
            'reviewer_name': 'Your Name',
            'body': 'Your Review',
        }
```

- [ ] **Step 4: Write `reviews/views.py`**

```python
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect

from services.models import Service
from .forms import ReviewForm


def add_review(request, slug):
    service = get_object_or_404(Service, slug=slug, is_active=True)
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.service = service
            review.save()
            messages.success(
                request,
                'Thanks! Your review has been submitted and is awaiting approval.',
            )
    return redirect('service_detail', slug=slug)
```

- [ ] **Step 5: Write `reviews/urls.py`**

```python
from django.urls import path
from . import views

urlpatterns = [
    path('services/<slug:slug>/reviews/add/', views.add_review, name='add_review'),
]
```

- [ ] **Step 6: Include `reviews.urls` in `config/urls.py`**

```python
urlpatterns = [
    path('admin/dashboard/', DashboardView.as_view(), name='admin_dashboard'),
    path('admin/', admin.site.urls),
    path('', include('services.urls')),
    path('bookings/', include('bookings.urls')),
    path('payments/', include('payments.urls')),
    path('', include('reviews.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

- [ ] **Step 7: Run tests — expect pass**

```bash
python manage.py test reviews.tests.ReviewFormTest reviews.tests.AddReviewViewTest --verbosity=2
```

Expected: `7 tests, 0 failures`

- [ ] **Step 8: Commit**

```bash
git add reviews/forms.py reviews/views.py reviews/urls.py config/urls.py reviews/tests.py
git commit -m "Add ReviewForm, add_review view, and URL wiring"
```

---

## Task 3: `ReviewAdmin` with bulk approve/reject actions

**Files:**
- Create: `reviews/admin.py`
- Modify: `reviews/tests.py` (add admin action tests)

- [ ] **Step 1: Add admin action tests to `reviews/tests.py`**

Append to the existing file:

```python
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
```

- [ ] **Step 2: Run tests — expect failure**

```bash
python manage.py test reviews.tests.ReviewAdminActionTest --verbosity=2
```

Expected: `NoReverseMatch` or 404 — admin not registered yet.

- [ ] **Step 3: Write `reviews/admin.py`**

```python
from django.contrib import admin
from .models import Review


@admin.action(description='Approve selected reviews')
def approve_selected(modeladmin, request, queryset):
    queryset.update(status=Review.STATUS_APPROVED)


@admin.action(description='Reject selected reviews')
def reject_selected(modeladmin, request, queryset):
    queryset.update(status=Review.STATUS_REJECTED)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('service', 'reviewer_name', 'rating', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('reviewer_name', 'body', 'service__name')
    readonly_fields = ('service', 'reviewer_name', 'rating', 'body', 'created_at')
    actions = [approve_selected, reject_selected]
```

- [ ] **Step 4: Run tests — expect pass**

```bash
python manage.py test reviews.tests.ReviewAdminActionTest --verbosity=2
```

Expected: `2 tests, 0 failures`

- [ ] **Step 5: Run the full test suite to confirm nothing broken**

```bash
python manage.py test reviews --verbosity=2
```

Expected: `13 tests, 0 failures`

- [ ] **Step 6: Commit**

```bash
git add reviews/admin.py reviews/tests.py
git commit -m "Add ReviewAdmin with bulk approve/reject actions"
```

---

## Task 4: Update `service_detail` view — reviews context + avg_rating

**Files:**
- Modify: `services/views.py`
- Modify: `reviews/tests.py` (add service detail context tests)

- [ ] **Step 1: Add context tests to `reviews/tests.py`**

Append to the existing file:

```python
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
```

- [ ] **Step 2: Run tests — expect failure**

```bash
python manage.py test reviews.tests.ServiceDetailContextTest --verbosity=2
```

Expected: `AssertionError` — `reviews` and `review_form` not in context yet.

- [ ] **Step 3: Update `service_detail` in `services/views.py`**

Replace the existing `service_detail` function:

```python
def service_detail(request, slug):
    from django.db.models import Avg, Q as Qdb
    from reviews.forms import ReviewForm
    from reviews.models import Review

    service = get_object_or_404(
        Service.objects.annotate(
            avg_rating=Avg(
                'reviews__rating',
                filter=Qdb(reviews__status=Review.STATUS_APPROVED),
            )
        ).select_related('vendor', 'category', 'city__district__state__country'),
        slug=slug, is_active=True,
    )
    attr_values = service.attribute_values.select_related('attribute').order_by('attribute__order')
    images = service.images.all()
    booked_dates = list(
        service.bookings.filter(status__in=['pending', 'confirmed']).values_list('event_date', flat=True)
    )
    blocked_dates = list(service.blocked_dates.values_list('date', flat=True))
    unavailable = sorted(set(booked_dates + blocked_dates))

    approved_reviews = Review.objects.filter(
        service=service, status=Review.STATUS_APPROVED
    ).order_by('-created_at')

    return render(request, 'services/detail.html', {
        'service': service,
        'attr_values': attr_values,
        'images': images,
        'unavailable_dates': [d.isoformat() for d in unavailable],
        'reviews': approved_reviews,
        'review_form': ReviewForm(),
    })
```

- [ ] **Step 4: Run tests — expect pass**

```bash
python manage.py test reviews.tests.ServiceDetailContextTest --verbosity=2
```

Expected: `4 tests, 0 failures`

- [ ] **Step 5: Run all reviews tests**

```bash
python manage.py test reviews --verbosity=2
```

Expected: `17 tests, 0 failures`

- [ ] **Step 6: Commit**

```bash
git add services/views.py reviews/tests.py
git commit -m "Extend service_detail view with reviews context and avg_rating annotation"
```

---

## Task 5: Update templates — reviews section + star badge

**Files:**
- Modify: `templates/services/detail.html`
- Modify: `templates/partials/service_card.html`

No new tests needed — the context is already tested; this is template rendering only.

- [ ] **Step 1: Add reviews section + form to `templates/services/detail.html`**

Find the closing `</div>` of the `col-lg-8` column (the left column, after the vendor contact card). Insert the following block **before** that closing `</div>`:

```html
      <!-- Reviews -->
      <div class="card border-0 bg-white shadow-sm rounded-3 p-3 mt-4">
        <h5 class="fw-bold mb-3">
          <i class="bi bi-star-half text-warning"></i> Reviews
          {% if service.avg_rating %}
          <span class="text-warning ms-1">
            {% for i in "12345" %}
              {% if forloop.counter <= service.avg_rating %}
                <i class="bi bi-star-fill"></i>
              {% else %}
                <i class="bi bi-star"></i>
              {% endif %}
            {% endfor %}
          </span>
          <span class="text-muted small fw-normal">({{ reviews|length }})</span>
          {% endif %}
        </h5>

        {% if reviews %}
          {% for review in reviews %}
          <div class="border-bottom pb-3 mb-3">
            <div class="d-flex align-items-center gap-2 mb-1">
              <span class="fw-semibold">{{ review.reviewer_name }}</span>
              <span class="text-warning small">
                {% for i in "12345" %}
                  {% if forloop.counter <= review.rating %}
                    <i class="bi bi-star-fill"></i>
                  {% else %}
                    <i class="bi bi-star"></i>
                  {% endif %}
                {% endfor %}
              </span>
              <span class="text-muted small">{{ review.created_at|date:"N j, Y" }}</span>
            </div>
            <p class="mb-0 small">{{ review.body }}</p>
          </div>
          {% endfor %}
        {% else %}
          <p class="text-muted small">No reviews yet — be the first!</p>
        {% endif %}

        <!-- Submission form -->
        <h6 class="fw-bold mt-3 mb-2">Leave a Review</h6>
        <form method="post" action="{% url 'add_review' service.slug %}">
          {% csrf_token %}
          <div class="mb-2">
            <label class="form-label small fw-semibold">{{ review_form.reviewer_name.label }}</label>
            {{ review_form.reviewer_name.errors }}
            <input type="text" name="reviewer_name" class="form-control form-control-sm"
                   placeholder="Your name" required>
          </div>
          <div class="mb-2">
            <label class="form-label small fw-semibold">Rating</label>
            {{ review_form.rating.errors }}
            <div class="d-flex gap-2 align-items-center">
              {% for val in "12345" %}
              <div class="form-check form-check-inline">
                <input class="form-check-input" type="radio" name="rating"
                       id="star{{ val }}" value="{{ val }}" required>
                <label class="form-check-label" for="star{{ val }}">{{ val }}★</label>
              </div>
              {% endfor %}
            </div>
          </div>
          <div class="mb-3">
            <label class="form-label small fw-semibold">{{ review_form.body.label }}</label>
            {{ review_form.body.errors }}
            <textarea name="body" class="form-control form-control-sm" rows="3"
                      placeholder="Share your experience…" required></textarea>
          </div>
          <button type="submit" class="btn btn-primary btn-sm">Submit Review</button>
        </form>
      </div>
```

The correct insertion point is right before the closing tag of the `col-lg-8` div — find the line containing:
```html
    </div>

    <!-- Right: booking panel -->
```
and insert the reviews card block just before that `</div>`.

- [ ] **Step 2: Add avg_rating badge to `templates/partials/service_card.html`**

Find the `mt-auto d-flex` price row in the card body:

```html
    <div class="mt-auto d-flex align-items-center justify-content-between">
```

Add the avg_rating badge immediately **before** that div:

```html
    {% if service.avg_rating %}
    <div class="mb-1">
      <span class="text-warning small">
        <i class="bi bi-star-fill"></i>
        {{ service.avg_rating|floatformat:1 }}
      </span>
      <span class="text-muted small">({{ service.review_count }} review{{ service.review_count|pluralize }})</span>
    </div>
    {% endif %}
```

**Note:** `avg_rating` and `review_count` must come from the view's queryset annotation. Update `service_list` in `services/views.py` to annotate with both:

```python
from django.db.models import Avg, Count, Q
from reviews.models import Review

def service_list(request, category_slug=None):
    services = Service.objects.filter(is_active=True).select_related(
        'vendor', 'category', 'city__district__state__country'
    ).annotate(
        avg_rating=Avg(
            'reviews__rating',
            filter=Q(reviews__status=Review.STATUS_APPROVED),
        ),
        review_count=Count(
            'reviews',
            filter=Q(reviews__status=Review.STATUS_APPROVED),
        ),
    )
    # ... rest of the function unchanged
```

Also add the same annotations to the `home` view's `featured` queryset:

```python
    featured = Service.objects.filter(is_active=True, is_featured=True).select_related(
        'vendor', 'category', 'city__district__state__country'
    ).annotate(
        avg_rating=Avg(
            'reviews__rating',
            filter=Q(reviews__status=Review.STATUS_APPROVED),
        ),
        review_count=Count(
            'reviews',
            filter=Q(reviews__status=Review.STATUS_APPROVED),
        ),
    )[:6]
```

Add `from reviews.models import Review` and update the existing `from django.db.models import Count, Q` import to also include `Avg` at the top of `services/views.py`.

- [ ] **Step 3: Start the dev server and manually verify**

```bash
python manage.py runserver
```

- Visit any service detail page — confirm the reviews section and form appear at the bottom of the left column.
- Submit a test review via the form — confirm the success flash message appears and you're redirected back.
- Log into `/admin/reviews/review/` — confirm the pending review appears; use the bulk action to approve it.
- Reload the service detail page — confirm the approved review appears in the reviews list.
- Visit the service list page — if the service now has ≥1 approved review, confirm the star badge appears on its card.

- [ ] **Step 4: Run the full test suite**

```bash
python manage.py test --verbosity=2
```

Expected: all tests pass, 0 failures.

- [ ] **Step 5: Commit**

```bash
git add templates/services/detail.html templates/partials/service_card.html services/views.py
git commit -m "Add reviews section and star badge to service templates"
```

---

## Task 6: Push to main

- [ ] **Step 1: Run full test suite one final time**

```bash
python manage.py test --verbosity=2
```

Expected: all tests pass.

- [ ] **Step 2: Push**

```bash
git push origin main
```
