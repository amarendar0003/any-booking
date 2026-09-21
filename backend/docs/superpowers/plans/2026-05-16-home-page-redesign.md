# Home Page Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the AnyBooking home page from a gradient-hero/icon-card layout to a photo-forward, Tagvenue-style design with a full-bleed hero, category photo tiles, benefit strip, and city photo cards.

**Architecture:** Add `image` to `Category` and `is_featured`/`image` to `City` models (one migration); update the home view to pass featured cities; rewrite `home.html` and update `base.html` (navbar) and `main.css`.

**Tech Stack:** Django 5.2, Bootstrap 5, Bootstrap Icons, Pillow (already installed), WhiteNoise static files.

**Test runner:** `python manage.py test services --verbosity=2`  
**Prerequisite:** PostgreSQL running and `DATABASE_URL` set (see CLAUDE.md).

---

## File Map

| File | Action |
|---|---|
| `services/models.py` | Add `Category.image`, `City.is_featured`, `City.image` |
| `services/migrations/XXXX_home_redesign.py` | Auto-generated migration |
| `services/admin.py` | Expose new fields in `CategoryAdmin` and `CityAdmin` |
| `services/views.py` | Add `featured_cities` queryset to `home()` |
| `services/tests.py` | New tests for models and home view |
| `static/img/hero.jpg` | New static hero image (~200 KB) |
| `static/css/main.css` | Replace hero styles; add tile/card/strip styles |
| `templates/base.html` | Navbar: dark-blue → white |
| `templates/home.html` | Full rewrite |

---

## Task 1: Model fields

**Files:**
- Modify: `services/models.py`
- Modify: `services/tests.py`

- [ ] **Step 1: Write failing tests**

Open `services/tests.py` and replace its contents:

```python
from django.test import TestCase, Client
from django.urls import reverse
from services.models import (
    Category, City, District, State, Country,
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


class HomeViewContextTest(TestCase):
    def setUp(self):
        self.client = Client()
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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
python manage.py test services.tests.CategoryImageFieldTest services.tests.CityFeaturedFieldsTest services.tests.HomeViewContextTest --verbosity=2
```

Expected: errors like `TypeError: City() got unexpected keyword argument 'is_featured'` and `AttributeError: 'Category' has no attribute 'image'`.

- [ ] **Step 3: Add fields to models**

In `services/models.py`, update the `Category` class (after the `is_active` field, line ~111):

```python
    is_active = models.BooleanField(default=True, help_text='Uncheck to hide this category from the public site')
    image = models.ImageField(upload_to='categories/', blank=True)
```

Update the `City` class (after the `is_active` field, line ~54):

```python
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False, help_text='Show on home page city cards')
    image = models.ImageField(upload_to='cities/', blank=True)
```

- [ ] **Step 4: Create and apply migration**

```bash
python manage.py makemigrations services --name home_redesign
python manage.py migrate
```

Expected: new file `services/migrations/XXXX_home_redesign.py` created; `migrate` succeeds with no errors.

- [ ] **Step 5: Run tests — expect pass**

```bash
python manage.py test services.tests.CategoryImageFieldTest services.tests.CityFeaturedFieldsTest --verbosity=2
```

Expected: `CategoryImageFieldTest` and `CityFeaturedFieldsTest` all PASS. `HomeViewContextTest` still fails (`featured_cities` not in context) — fix in Task 3.

- [ ] **Step 6: Commit**

```bash
git add services/models.py services/migrations/ services/tests.py
git commit -m "Add image field to Category and is_featured/image to City"
```

---

## Task 2: Admin — expose new fields

**Files:**
- Modify: `services/admin.py`

- [ ] **Step 1: Update CategoryAdmin**

Find the `CategoryAdmin` class (around line 87) and add `fieldsets`:

```python
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'slug', 'icon', 'is_active', 'service_count')
    list_editable = ('is_active',)
    list_filter = ('is_active',)
    fieldsets = (
        ('Details', {
            'fields': ('slug', 'description', 'icon', 'is_active'),
        }),
        ('Home Page', {
            'description': 'Upload a photo to show on the home page category tile.',
            'fields': ('image',),
        }),
    )

    def service_count(self, obj):
        return obj.services.filter(is_active=True).count()
    service_count.short_description = 'Active Services'
```

- [ ] **Step 2: Update CityAdmin**

Find the `CityAdmin` class (around line 69) and update it:

```python
@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ('name', 'district', 'state_name', 'country_name', 'pin_code', 'is_active', 'is_featured')
    list_filter = ('district__state__country', 'district__state', 'is_active', 'is_featured')
    list_editable = ('is_featured',)
    search_fields = ('name', 'pin_code')
    fieldsets = (
        ('Details', {
            'fields': ('district', 'name', 'pin_code', 'is_active'),
        }),
        ('Home Page', {
            'description': 'Tick to pin this city on the home page. Upload a photo for the city card.',
            'fields': ('is_featured', 'image'),
        }),
    )

    def state_name(self, obj):
        return obj.state.name
    state_name.short_description = 'State'

    def country_name(self, obj):
        return obj.country.name
    country_name.short_description = 'Country'
```

- [ ] **Step 3: Verify admin loads without error**

```bash
python manage.py check
```

Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 4: Commit**

```bash
git add services/admin.py
git commit -m "Expose Category.image and City.is_featured/image in admin"
```

---

## Task 3: Home view — featured cities

**Files:**
- Modify: `services/views.py`

- [ ] **Step 1: Update the home view**

In `services/views.py`, update the `home()` function to add the `featured_cities` queryset:

```python
def home(request):
    pref_country_id = request.COOKIES.get('ab_country', '')
    pref_state_id = request.COOKIES.get('ab_state', '')

    categories = Category.objects.filter(is_active=True).annotate(
        filtered_count=Count('services', filter=_category_loc_filter(pref_country_id, pref_state_id))
    )
    featured = Service.objects.filter(is_active=True, is_featured=True).select_related(
        'vendor', 'category', 'city__district__state__country'
    )[:6]
    featured_cities = City.objects.filter(is_featured=True, is_active=True).order_by('name')[:6]
    countries = Country.objects.filter(is_active=True)

    return render(request, 'home.html', {
        'categories': categories,
        'featured': featured,
        'featured_cities': featured_cities,
        'countries': countries,
        'pref_country_id': pref_country_id,
        'pref_state_id': pref_state_id,
    })
```

Also update the import line at the top of `views.py` (City is already imported — no change needed).

- [ ] **Step 2: Run all tests**

```bash
python manage.py test services --verbosity=2
```

Expected: all tests PASS including `HomeViewContextTest`.

- [ ] **Step 3: Commit**

```bash
git add services/views.py
git commit -m "Home view: add featured_cities context for city card section"
```

---

## Task 4: Hero image

**Files:**
- Create: `static/img/hero.jpg`

- [ ] **Step 1: Create the img directory and download the hero image**

```bash
mkdir -p static/img
curl -L "https://images.unsplash.com/photo-1519167758481-83f550bb49b3?w=1400&q=75&fm=jpg" \
  -o static/img/hero.jpg
```

- [ ] **Step 2: Verify the file exists and is a valid image**

```bash
file static/img/hero.jpg
ls -lh static/img/hero.jpg
```

Expected: output shows `JPEG image data` and size under 400 KB (Unsplash serves optimised images).

- [ ] **Step 3: Commit**

```bash
git add static/img/hero.jpg
git commit -m "Add hero image for home page redesign"
```

---

## Task 5: CSS — new styles

**Files:**
- Modify: `static/css/main.css`

- [ ] **Step 1: Replace the hero block and add all new styles**

Open `static/css/main.css`. Replace the entire `/* Hero */` block (lines 11–17) and append new sections. The full updated file content:

```css
:root {
  --primary: #1a56db;
  --accent: #f59e0b;
}

body { background: #f8f9fa; }

.navbar-brand { letter-spacing: -0.5px; }

/* ── Hero ─────────────────────────────────────────────────────────────────── */
.hero {
  position: relative;
  height: 420px;
  overflow: hidden;
}
.hero-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.hero-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(to bottom, rgba(0,0,0,.45), rgba(0,0,0,.60));
}
.hero-content {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 0 24px;
  text-align: center;
}
.hero-content h1 {
  color: white;
  font-size: 2.4rem;
  font-weight: 800;
  margin-bottom: 10px;
  letter-spacing: -.5px;
}
.hero-content p {
  color: rgba(255,255,255,.88);
  font-size: 1.05rem;
  margin-bottom: 24px;
}
.hero-search {
  background: white;
  border-radius: 12px;
  padding: 10px 12px;
  display: flex;
  gap: 10px;
  align-items: center;
  width: 100%;
  max-width: 580px;
  box-shadow: 0 8px 32px rgba(0,0,0,.2);
}
.hero-search input {
  border: none;
  outline: none;
  flex: 1;
  font-size: .92rem;
  color: #333;
  background: transparent;
}
.hero-search button {
  background: var(--primary);
  color: white;
  border: none;
  border-radius: 8px;
  padding: 9px 20px;
  font-size: .88rem;
  font-weight: 700;
  cursor: pointer;
  white-space: nowrap;
}
@media (max-width: 576px) {
  .hero { height: 280px; }
  .hero-content h1 { font-size: 1.6rem; }
  .hero-content p { font-size: .88rem; }
}

/* ── Category tiles ───────────────────────────────────────────────────────── */
.cat-tile {
  position: relative;
  border-radius: 14px;
  overflow: hidden;
  height: 120px;
  display: block;
  text-decoration: none;
}
.cat-tile img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform .3s;
}
.cat-tile:hover img { transform: scale(1.05); }
.cat-tile-fallback {
  width: 100%;
  height: 100%;
  background: #e9ecef;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2.2rem;
  color: #6c757d;
}
.cat-tile-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(to top, rgba(0,0,0,.65), rgba(0,0,0,.10));
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  padding: 10px 12px;
}
.cat-tile-name {
  color: white;
  font-size: .88rem;
  font-weight: 700;
}
.cat-tile-count {
  color: rgba(255,255,255,.75);
  font-size: .72rem;
  margin-top: 1px;
}
.cat-tile-viewall {
  background: #e9ecef;
  border-radius: 14px;
  height: 120px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  text-decoration: none;
  color: #6c757d;
  font-size: .82rem;
  font-weight: 600;
  transition: background .2s, color .2s;
}
.cat-tile-viewall:hover { background: #dee2e6; color: #495057; }

/* ── Benefit strip ────────────────────────────────────────────────────────── */
.benefit-strip {
  background: white;
  border-top: 1px solid #e9ecef;
  border-bottom: 1px solid #e9ecef;
  padding: 40px 0;
}
.benefit { text-align: center; }
.benefit-icon { font-size: 2rem; margin-bottom: 10px; }
.benefit h4 { font-size: .95rem; font-weight: 700; margin-bottom: 4px; }
.benefit p { font-size: .82rem; color: #666; margin: 0; }

/* ── City cards ───────────────────────────────────────────────────────────── */
.city-card {
  position: relative;
  border-radius: 14px;
  overflow: hidden;
  height: 130px;
  display: block;
  text-decoration: none;
}
.city-card img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform .3s;
}
.city-card:hover img { transform: scale(1.05); }
.city-card-fallback {
  width: 100%;
  height: 100%;
  background: #dee2e6;
  display: flex;
  align-items: center;
  justify-content: center;
}
.city-card-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0,0,0,.40);
  display: flex;
  align-items: center;
  justify-content: center;
}
.city-card-name {
  color: white;
  font-size: 1rem;
  font-weight: 800;
  text-shadow: 0 2px 6px rgba(0,0,0,.4);
}

/* ── Service cards ────────────────────────────────────────────────────────── */
.service-card {
  border: none;
  border-radius: 14px;
  overflow: hidden;
  transition: transform 0.2s, box-shadow 0.2s;
}
.service-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 10px 24px rgba(0,0,0,.10);
}
.service-card .card-img-top {
  height: 190px;
  object-fit: cover;
  background: #e9ecef;
}
.service-card .img-placeholder {
  height: 190px;
  background: linear-gradient(135deg, #e9ecef, #dee2e6);
  display: flex; align-items: center; justify-content: center;
  font-size: 3rem; color: #adb5bd;
}
.badge-featured {
  position: absolute; top: 12px; left: 12px;
  background: var(--accent);
  color: #1a1a1a;
  font-weight: 600;
}

/* ── How It Works strip ───────────────────────────────────────────────────── */
.hiw-strip {
  background: white;
  border-top: 1px solid #e9ecef;
  padding: 48px 0;
}

/* ── Attribute badges ─────────────────────────────────────────────────────── */
.attr-badge {
  display: inline-flex; align-items: center; gap: 4px;
  background: #eef2ff;
  color: #3730a3;
  border-radius: 6px;
  padding: 3px 10px;
  font-size: 0.82rem;
  font-weight: 500;
  margin: 2px;
}
.attr-badge.attr-yes { background: #dcfce7; color: #166534; }
.attr-badge.attr-no  { background: #fee2e2; color: #991b1b; }

/* ── Sidebar filters ──────────────────────────────────────────────────────── */
.filter-sidebar { position: sticky; top: 20px; }
.filter-sidebar .card {
  border: none;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,.07);
}

/* ── Availability calendar ────────────────────────────────────────────────── */
.calendar-day {
  width: 36px; height: 36px;
  border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  font-size: 0.85rem;
  cursor: default;
}
.calendar-day.available { background: #dcfce7; color: #166534; cursor: pointer; }
.calendar-day.available:hover { background: #16a34a; color: white; }
.calendar-day.unavailable { background: #fee2e2; color: #991b1b; text-decoration: line-through; }
.calendar-day.selected { background: var(--primary); color: white; }
.calendar-day.other-month { opacity: 0.35; }

/* ── Breadcrumb ───────────────────────────────────────────────────────────── */
.breadcrumb-hero {
  background: #eef2ff;
  padding: 10px 0;
  border-bottom: 1px solid #e0e7ff;
}
```

- [ ] **Step 2: Verify Django can still collect static without error**

```bash
python manage.py collectstatic --no-input 2>&1 | tail -5
```

Expected: ends with something like `X static files copied to 'staticfiles'` or `X post-processed` — no errors.

- [ ] **Step 3: Commit**

```bash
git add static/css/main.css
git commit -m "CSS: photo-forward hero, category tiles, city cards, benefit strip"
```

---

## Task 6: Navbar — white theme

**Files:**
- Modify: `templates/base.html`

- [ ] **Step 1: Update the navbar classes and link colours**

In `templates/base.html`, find the `<nav>` tag (line 15). Replace:

```html
<nav class="navbar navbar-expand-lg navbar-dark bg-primary shadow-sm">
```

with:

```html
<nav class="navbar navbar-expand-lg bg-white border-bottom shadow-sm">
```

Find the nav-link styles — they currently rely on Bootstrap's `navbar-dark` to make links white. Add explicit colour by updating all `<a class="nav-link"` tags to include `style="color:#555"` isn't clean — instead, wrap with a custom class. Replace the entire `<ul class="navbar-nav me-auto">` block:

```html
      <ul class="navbar-nav me-auto">
        <li class="nav-item"><a class="nav-link text-secondary" href="{% url 'service_list' %}">All Services</a></li>
        {% for cat in nav_categories %}
        <li class="nav-item">
          <a class="nav-link text-secondary" href="{% url 'service_list_by_category' cat.slug %}">{{ cat|local_cat_name:request }}</a>
        </li>
        {% endfor %}
        <li class="nav-item">
          <a class="nav-link text-secondary" href="{% url 'booking_lookup' %}">
            <i class="bi bi-search"></i> Find My Booking
          </a>
        </li>
      </ul>
```

Update the location indicator text colours (currently `text-white-50`, `text-white`) to dark-mode equivalents. Replace the location indicator block:

```html
      <!-- Location indicator -->
      <div class="me-3 d-flex align-items-center">
        {% if pref_country %}
        <span class="text-muted small me-1"><i class="bi bi-geo-alt-fill text-warning"></i></span>
        <span class="text-secondary small">
          {% if pref_state %}{{ pref_state.name }}, {% endif %}{{ pref_country.name }}
        </span>
        <button class="btn btn-link btn-sm text-muted p-0 ms-2 change-location-btn" style="font-size:.75rem" onclick="openLocationModal()">
          Change
        </button>
        {% else %}
        <button class="btn btn-outline-secondary btn-sm py-0 px-2 change-location-btn" style="font-size:.8rem" onclick="openLocationModal()">
          <i class="bi bi-geo-alt"></i> Set Location
        </button>
        {% endif %}
      </div>

      <a href="/admin/" class="btn btn-outline-primary btn-sm">
        <i class="bi bi-person-gear"></i> Admin
      </a>
```

- [ ] **Step 2: Verify the page renders**

```bash
python manage.py runserver 8000
```

Open `http://127.0.0.1:8000` and confirm the navbar is now white with dark links. Stop the server (`Ctrl+C`).

- [ ] **Step 3: Simplify footer**

In `templates/base.html`, find the `<footer>` tag (line ~134). Replace:

```html
<footer class="bg-dark text-white mt-5 py-4">
  <div class="container text-center">
    <p class="mb-1">&copy; 2025 AnyBooking. All rights reserved.</p>
    <small class="text-muted">Banquet Halls · Music Bands · Catering · Hotels &amp; more</small>
  </div>
</footer>
```

with:

```html
<footer style="background:#111;color:#aaa;" class="mt-5 py-4">
  <div class="container text-center">
    <p class="mb-0 small"><strong class="text-white">AnyBooking</strong> &copy; 2025 · Banquet Halls · Music Bands · Catering · Hotels &amp; more</p>
  </div>
</footer>
```

- [ ] **Step 4: Commit**

```bash
git add templates/base.html
git commit -m "Navbar: white theme; footer: minimal dark #111"
```

---

## Task 7: Home template — full rewrite

**Files:**
- Modify: `templates/home.html`

- [ ] **Step 1: Replace home.html**

Replace the entire contents of `templates/home.html` with:

```html
{% extends 'base.html' %}
{% load static local_names %}
{% block title %}Home{% endblock %}

{% block content %}

{# ── Hero ──────────────────────────────────────────────────────────────── #}
<div class="hero">
  <img class="hero-img" src="{% static 'img/hero.jpg' %}" alt="Venue">
  <div class="hero-overlay"></div>
  <div class="hero-content">
    <h1>Find &amp; Book the Perfect Venue</h1>
    <p>Banquet halls, music bands, catering, hotels &amp; more — across India and beyond</p>
    <form method="get" action="{% url 'service_list' %}" class="hero-search">
      <i class="bi bi-search text-muted"></i>
      <input name="q" placeholder="Search venues, services, cities…" value="{{ request.GET.q }}" autocomplete="off">
      <button type="submit">Search</button>
    </form>
  </div>
</div>

{# ── Category tiles ────────────────────────────────────────────────────── #}
<section class="container my-5">
  <h2 class="fw-bold mb-4">Browse by Category</h2>
  <div class="row g-3">
    {% for cat in categories %}
    <div class="col-6 col-sm-4 col-md-3 col-lg-2">
      <a href="{% url 'service_list_by_category' cat.slug %}" class="cat-tile">
        {% if cat.image %}
          <img src="{{ cat.image.url }}" alt="{{ cat|local_cat_name:request }}">
        {% else %}
          <div class="cat-tile-fallback">
            <i class="bi {{ cat.icon }}"></i>
          </div>
        {% endif %}
        <div class="cat-tile-overlay">
          <div class="cat-tile-name">{{ cat|local_cat_name:request }}</div>
          <div class="cat-tile-count">{{ cat.filtered_count }} listing{{ cat.filtered_count|pluralize }}</div>
        </div>
      </a>
    </div>
    {% empty %}
    <p class="text-muted">No categories configured yet. <a href="/admin/">Add via admin</a>.</p>
    {% endfor %}
    {% if categories %}
    <div class="col-6 col-sm-4 col-md-3 col-lg-2">
      <a href="{% url 'service_list' %}" class="cat-tile-viewall">
        <i class="bi bi-grid fs-4"></i>
        <span>View All</span>
      </a>
    </div>
    {% endif %}
  </div>
</section>

{# ── Benefit strip ─────────────────────────────────────────────────────── #}
<div class="benefit-strip">
  <div class="container">
    <div class="row g-4">
      <div class="col-md-4 benefit">
        <div class="benefit-icon">✅</div>
        <h4>Verified Listings</h4>
        <p>Every vendor is reviewed before going live</p>
      </div>
      <div class="col-md-4 benefit">
        <div class="benefit-icon">🔒</div>
        <h4>Secure Payments</h4>
        <p>Razorpay-backed advance — safe &amp; instant</p>
      </div>
      <div class="col-md-4 benefit">
        <div class="benefit-icon">📅</div>
        <h4>Real Availability</h4>
        <p>Live calendar — no double-bookings, no surprises</p>
      </div>
    </div>
  </div>
</div>

{# ── Popular cities ────────────────────────────────────────────────────── #}
{% if featured_cities %}
<section class="container my-5">
  <h2 class="fw-bold mb-4">Popular Cities</h2>
  <div class="row g-3">
    {% for city in featured_cities %}
    <div class="col-6 col-sm-4 col-md-3 col-lg-2">
      <a href="{% url 'service_list' %}?city={{ city.id }}" class="city-card">
        {% if city.image %}
          <img src="{{ city.image.url }}" alt="{{ city.name }}">
        {% else %}
          <div class="city-card-fallback"></div>
        {% endif %}
        <div class="city-card-overlay">
          <span class="city-card-name">{{ city.name }}</span>
        </div>
      </a>
    </div>
    {% endfor %}
  </div>
</section>
{% endif %}

{# ── Featured listings ─────────────────────────────────────────────────── #}
{% if featured %}
<section class="container my-5">
  <h2 class="fw-bold mb-4">Featured Listings</h2>
  <div class="row g-4">
    {% for svc in featured %}
    <div class="col-sm-6 col-lg-4">
      {% include 'partials/service_card.html' with service=svc %}
    </div>
    {% endfor %}
  </div>
  <div class="text-center mt-4">
    <a href="{% url 'service_list' %}" class="btn btn-outline-primary btn-lg px-5">View All Services</a>
  </div>
</section>
{% endif %}

{# ── How it works ──────────────────────────────────────────────────────── #}
<div class="hiw-strip">
  <div class="container">
    <h2 class="fw-bold mb-4 text-center">How It Works</h2>
    <div class="row g-4 text-center">
      <div class="col-md-3">
        <div class="display-5 text-primary mb-2"><i class="bi bi-search"></i></div>
        <h6 class="fw-bold">1. Browse</h6>
        <p class="text-muted small">Search by category, city, or keyword</p>
      </div>
      <div class="col-md-3">
        <div class="display-5 text-primary mb-2"><i class="bi bi-calendar2-check"></i></div>
        <h6 class="fw-bold">2. Check Availability</h6>
        <p class="text-muted small">Pick a date and see real-time availability</p>
      </div>
      <div class="col-md-3">
        <div class="display-5 text-primary mb-2"><i class="bi bi-pencil-square"></i></div>
        <h6 class="fw-bold">3. Book</h6>
        <p class="text-muted small">Fill in your details and submit the request</p>
      </div>
      <div class="col-md-3">
        <div class="display-5 text-primary mb-2"><i class="bi bi-credit-card"></i></div>
        <h6 class="fw-bold">4. Pay &amp; Confirm</h6>
        <p class="text-muted small">Secure online advance payment via Razorpay</p>
      </div>
    </div>
  </div>
</div>

{% endblock %}

{% block extra_js %}
<script>
const ajaxUrl = "{% url 'location_ajax' %}";
const prefCountryId = "{{ pref_country_id }}";
const prefStateId = "{{ pref_state_id }}";

async function loadOptions(kind, parentId, targetId, label, preselectId) {
  const sel = document.getElementById(targetId);
  sel.innerHTML = `<option value="">All ${label}</option>`;
  if (!parentId) return;
  const r = await fetch(`${ajaxUrl}?kind=${kind}&parent_id=${parentId}`);
  const data = await r.json();
  data.results.forEach(item => {
    const opt = document.createElement('option');
    opt.value = item.id;
    opt.textContent = item.name;
    if (preselectId && item.id == preselectId) opt.selected = true;
    sel.appendChild(opt);
  });
}

async function loadStates(id, preselectId) {
  await loadOptions('states', id, 'loc-state', 'States', preselectId);
  document.getElementById('loc-district').innerHTML = '<option value="">All Districts</option>';
  document.getElementById('loc-city').innerHTML = '<option value="">All Cities</option>';
}
async function loadDistricts(id, preselectId) {
  await loadOptions('districts', id, 'loc-district', 'Districts', preselectId);
  document.getElementById('loc-city').innerHTML = '<option value="">All Cities</option>';
}
function loadCities(id) { loadOptions('cities', id, 'loc-city', 'Cities'); }

document.addEventListener('DOMContentLoaded', function () {
  if (prefCountryId) {
    loadStates(prefCountryId, prefStateId);
  }
});
</script>
{% endblock %}
```

- [ ] **Step 2: Run the full test suite**

```bash
python manage.py test services --verbosity=2
```

Expected: all tests PASS.

- [ ] **Step 3: Verify in browser**

```bash
python manage.py runserver 8000
```

Open `http://127.0.0.1:8000` and confirm:
- Photo hero with search pill
- Category tiles (icon fallback since no photos uploaded yet)
- Benefit strip (3 icons)
- No city section (no cities featured yet — section is hidden when queryset is empty)
- Featured listings section (if any featured services exist)
- How It Works section
- White navbar

Stop the server (`Ctrl+C`).

- [ ] **Step 4: Commit**

```bash
git add templates/home.html
git commit -m "Home page: photo hero, category tiles, benefit strip, city cards"
```

---

## Task 8: Final check

- [ ] **Step 1: Run full test suite**

```bash
python manage.py test services --verbosity=2
```

Expected: all tests PASS with no warnings.

- [ ] **Step 2: System check**

```bash
python manage.py check --deploy 2>&1 | grep -v "WARNINGS\|settings.DEBUG\|SECURE\|HSTS\|CSRF\|SESSION"
```

Expected: `System check identified no issues` (deployment warnings about HTTPS are expected in local dev).

- [ ] **Step 3: Verify the location-preference modal still works**

Start the server, open the home page in a private/incognito window. Confirm the "Set Location" modal appears on first visit and the location indicator updates in the navbar after saving.

- [ ] **Step 4: Commit (if any loose files remain)**

```bash
git status
```

If clean, nothing to do. If any untracked files remain, stage and commit them.
