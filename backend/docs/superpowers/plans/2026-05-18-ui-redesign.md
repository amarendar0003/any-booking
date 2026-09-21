# AnyBooking UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the public-facing UI (home, service list, service detail) and upgrade Django admin to Unfold, applying the Modern & Elegant brand identity with Inter font and sky-blue palette.

**Architecture:** CSS-only changes to public templates + full rewrite of `static/css/main.css`; Inter font via Google Fonts CDN in `base.html`; `django-unfold` package for admin with sky-blue theme in `settings.py`. No new Django apps, no model changes, no URL changes.

**Tech Stack:** Django 5.2, Bootstrap 5, Bootstrap Icons, Inter (Google Fonts), django-unfold 0.x, vanilla JS (existing unchanged)

**Design spec:** `docs/superpowers/specs/2026-05-17-ui-redesign-design.md`

---

## File Map

| File | Action |
|------|--------|
| `static/css/main.css` | Full rewrite — new design tokens + all component styles |
| `templates/base.html` | Add Inter `<link>`; restyle navbar + footer |
| `templates/home.html` | Full rewrite — gradient hero, category grid, featured grid, city strip, benefits |
| `templates/partials/service_card.html` | Full rewrite — photo-first card with attribute chips |
| `templates/services/list.html` | Full rewrite — navy header, sidebar pills, 2-col grid |
| `templates/services/detail.html` | Full rewrite — restyled carousel, features grid, reviews, sticky booking panel |
| `requirements.txt` | Add `django-unfold` |
| `config/settings.py` | Add `"unfold"` to INSTALLED_APPS; add UNFOLD config dict |
| `services/admin.py` | Add `from unfold.admin import ModelAdmin` |
| `bookings/admin.py` | Add `from unfold.admin import ModelAdmin` |
| `payments/admin.py` | Add `from unfold.admin import ModelAdmin` |
| `terms/admin.py` | Add `from unfold.admin import ModelAdmin` |
| `reviews/admin.py` | Add `from unfold.admin import ModelAdmin` |
| `templates/admin/base_site.html` | Extend `unfold/base_site.html` |
| `templates/admin/dashboard.html` | Update to Unfold content block |

---

## Task 1: CSS Design System + Base Template

**Files:**
- Modify: `static/css/main.css` (full rewrite)
- Modify: `templates/base.html`

- [ ] **Step 1: Rewrite `static/css/main.css`**

Replace the entire file with:

```css
/* ── Design tokens ──────────────────────────────────────────────────────── */
:root {
  --primary:       #0ea5e9;
  --primary-dark:  #0369a1;
  --navy:          #0f172a;
  --accent:        #f59e0b;
  --bg-page:       #f8fafc;
  --border:        #e2e8f0;
  --text-primary:  #0f172a;
  --text-secondary:#64748b;
  --text-muted:    #94a3b8;
  --success-bg:    #dcfce7;
  --success-text:  #166534;
  --danger-bg:     #fee2e2;
  --danger-text:   #991b1b;
  --radius-card:   16px;
}

body {
  font-family: 'Inter', sans-serif;
  background: var(--bg-page);
  color: var(--text-primary);
}

/* ── Navbar ─────────────────────────────────────────────────────────────── */
.navbar {
  background: white !important;
  border-bottom: 1px solid var(--border);
  box-shadow: 0 1px 4px rgba(0,0,0,.06);
  min-height: 60px;
}
.navbar-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 700;
  font-size: 1.1rem;
  color: var(--text-primary) !important;
  letter-spacing: -0.3px;
}
.navbar-brand .brand-icon {
  width: 32px;
  height: 32px;
  background: var(--primary);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: .9rem;
}
.navbar .nav-link {
  color: var(--text-secondary) !important;
  font-weight: 500;
  font-size: .9rem;
}
.navbar .nav-link:hover { color: var(--text-primary) !important; }

.location-badge {
  background: #f0f9ff;
  border: 1px solid #bae6fd;
  border-radius: 999px;
  padding: 4px 12px;
  font-size: .8rem;
  color: var(--primary-dark);
  display: flex;
  align-items: center;
  gap: 6px;
}
.btn-admin-cta {
  background: var(--primary);
  color: white !important;
  border: none;
  border-radius: 8px;
  font-weight: 700;
  font-size: .85rem;
  padding: 6px 16px;
}
.btn-admin-cta:hover { background: var(--primary-dark); }

/* ── Hero ───────────────────────────────────────────────────────────────── */
.hero {
  background: linear-gradient(140deg, #0f172a 0%, #1e3a5f 55%, #0369a1 100%);
  height: 520px;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 0 24px;
  position: relative;
}
@media (max-width: 576px) { .hero { height: 360px; } }

.hero-eyebrow {
  color: #7dd3fc;
  font-size: .75rem;
  font-weight: 700;
  letter-spacing: 2px;
  text-transform: uppercase;
  margin-bottom: 12px;
}
.hero-content h1 {
  color: white;
  font-size: 2.6rem;
  font-weight: 900;
  letter-spacing: -1.5px;
  margin-bottom: 14px;
  line-height: 1.15;
}
@media (max-width: 576px) { .hero-content h1 { font-size: 1.7rem; } }
.hero-content h1 .hero-accent { color: #38bdf8; }
.hero-content .hero-sub {
  color: rgba(255,255,255,.75);
  font-size: 1rem;
  margin-bottom: 28px;
}
.hero-search {
  background: white;
  border-radius: 14px;
  padding: 10px 12px;
  display: flex;
  gap: 10px;
  align-items: center;
  width: 100%;
  max-width: 580px;
  margin: 0 auto 28px;
  box-shadow: 0 20px 48px rgba(0,0,0,.25);
}
.hero-search input {
  border: none;
  outline: none;
  flex: 1;
  font-size: .92rem;
  font-family: 'Inter', sans-serif;
  color: var(--text-primary);
  background: transparent;
}
.hero-search button {
  background: var(--primary);
  color: white;
  border: none;
  border-radius: 10px;
  padding: 9px 22px;
  font-size: .88rem;
  font-weight: 700;
  font-family: 'Inter', sans-serif;
  cursor: pointer;
  white-space: nowrap;
}
.hero-search button:hover { background: var(--primary-dark); }

.hero-stats {
  display: flex;
  gap: 32px;
  justify-content: center;
  flex-wrap: wrap;
}
.hero-stat-num {
  color: white;
  font-size: 1.4rem;
  font-weight: 800;
  letter-spacing: -0.5px;
}
.hero-stat-label {
  color: rgba(255,255,255,.55);
  font-size: .75rem;
  margin-top: 2px;
}

/* ── Section headings ───────────────────────────────────────────────────── */
.section-title {
  font-size: 1.35rem;
  font-weight: 800;
  letter-spacing: -0.5px;
  color: var(--text-primary);
  margin-bottom: 20px;
}

/* ── Category tiles ─────────────────────────────────────────────────────── */
.cat-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
}
@media (max-width: 768px) { .cat-grid { grid-template-columns: repeat(2, 1fr); } }

.cat-tile {
  position: relative;
  border-radius: 14px;
  overflow: hidden;
  height: 140px;
  display: block;
  text-decoration: none;
  transition: transform .25s;
}
.cat-tile:hover { transform: scale(1.03); }
.cat-tile:hover .cat-tile-overlay { background: linear-gradient(to top, rgba(15,23,42,.85), rgba(3,105,161,.4)); }

.cat-tile-bg {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2rem;
}
.cat-tile-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(to top, rgba(0,0,0,.65), rgba(0,0,0,.15));
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  padding: 10px 12px;
  transition: background .25s;
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
  background: #f0f9ff;
  border: 2px dashed #bae6fd;
  border-radius: 14px;
  height: 140px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  text-decoration: none;
  color: var(--primary);
  font-size: .82rem;
  font-weight: 600;
  transition: background .2s;
}
.cat-tile-viewall:hover { background: #e0f2fe; color: var(--primary-dark); }

/* Category gradients */
.cat-bg-banquet   { background: linear-gradient(135deg, #1e3a5f, #0369a1); }
.cat-bg-music     { background: linear-gradient(135deg, #14532d, #166534); }
.cat-bg-catering  { background: linear-gradient(135deg, #7c2d12, #92400e); }
.cat-bg-hotels    { background: linear-gradient(135deg, #1e1b4b, #3730a3); }
.cat-bg-dancing   { background: linear-gradient(135deg, #4c1d95, #6d28d9); }
.cat-bg-priests   { background: linear-gradient(135deg, #7f1d1d, #991b1b); }
.cat-bg-events    { background: linear-gradient(135deg, #064e3b, #065f46); }
.cat-bg-default   { background: linear-gradient(135deg, #0f172a, #1e3a5f); }

/* ── Featured service cards ─────────────────────────────────────────────── */
.service-card {
  background: white;
  border-radius: var(--radius-card);
  border: 1px solid var(--border);
  overflow: hidden;
  transition: transform .2s, box-shadow .2s, border-color .2s;
  display: flex;
  flex-direction: column;
  height: 100%;
}
.service-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 32px rgba(0,0,0,.12);
  border-color: #bae6fd;
}
.service-card .card-img-top {
  height: 180px;
  object-fit: cover;
}
.service-card .img-placeholder {
  height: 180px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 3rem;
}
.service-card .card-body {
  padding: 16px;
  display: flex;
  flex-direction: column;
  flex: 1;
}
.badge-featured {
  position: absolute;
  top: 10px;
  left: 10px;
  background: var(--accent);
  color: #1a1a1a;
  font-weight: 700;
  font-size: .72rem;
  border-radius: 6px;
  padding: 3px 8px;
}
.badge-category {
  background: #eff6ff;
  color: var(--primary-dark);
  font-size: .72rem;
  font-weight: 600;
  border-radius: 6px;
  padding: 2px 8px;
}
.service-price {
  font-size: 1.05rem;
  font-weight: 800;
  color: var(--primary);
}
.btn-view {
  background: #eff6ff;
  color: var(--primary-dark);
  border: none;
  border-radius: 8px;
  font-size: .82rem;
  font-weight: 600;
  padding: 5px 14px;
  text-decoration: none;
  transition: background .15s, color .15s;
}
.btn-view:hover { background: var(--primary); color: white; }

/* ── City strip ─────────────────────────────────────────────────────────── */
.city-strip {
  background: #f0f9ff;
  border-top: 1px solid #e0f2fe;
  border-bottom: 1px solid #e0f2fe;
  padding: 40px 0;
}
.city-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 12px;
}
@media (max-width: 992px) { .city-grid { grid-template-columns: repeat(3, 1fr); } }
@media (max-width: 576px)  { .city-grid { grid-template-columns: repeat(2, 1fr); } }

.city-card {
  position: relative;
  border-radius: 12px;
  overflow: hidden;
  height: 100px;
  display: block;
  text-decoration: none;
  transition: transform .25s;
}
.city-card:hover { transform: scale(1.04); }
.city-card-bg {
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, #0f172a, #1e3a5f);
  object-fit: cover;
}
.city-card-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0,0,0,.38);
  display: flex;
  align-items: center;
  justify-content: center;
}
.city-card-name {
  color: white;
  font-size: .95rem;
  font-weight: 800;
  text-shadow: 0 2px 6px rgba(0,0,0,.4);
}

/* ── Benefits strip ─────────────────────────────────────────────────────── */
.benefit-strip {
  background: white;
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
  padding: 40px 0;
}
.benefit-icon-box {
  width: 48px;
  height: 48px;
  background: #eff6ff;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.3rem;
  color: var(--primary);
  margin-bottom: 12px;
}
.benefit h5 {
  font-size: .9rem;
  font-weight: 700;
  margin-bottom: 4px;
  color: var(--text-primary);
}
.benefit p {
  font-size: .8rem;
  color: var(--text-secondary);
  margin: 0;
}

/* ── Footer ─────────────────────────────────────────────────────────────── */
.site-footer {
  background: #0f172a;
  color: #94a3b8;
  padding: 28px 0;
}
.site-footer .brand-name { color: white; font-weight: 700; }
.site-footer a { color: #64748b; text-decoration: none; font-size: .82rem; }
.site-footer a:hover { color: #94a3b8; }

/* ── List page header ───────────────────────────────────────────────────── */
.list-header {
  background: linear-gradient(140deg, #0f172a 0%, #1e3a5f 55%, #0369a1 100%);
  padding: 28px 32px;
}
.list-header h1 {
  color: white;
  font-size: 1.6rem;
  font-weight: 800;
  margin-bottom: 4px;
}
.list-header .list-sub { color: rgba(255,255,255,.65); font-size: .88rem; }

/* ── List search strip ──────────────────────────────────────────────────── */
.search-strip {
  background: white;
  border-bottom: 1px solid var(--border);
  padding: 12px 0;
}
.search-strip .form-control,
.search-strip .form-select {
  border: 1.5px solid var(--border);
  border-radius: 9px;
  font-size: .85rem;
}
.search-strip .form-control:focus,
.search-strip .form-select:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(14,165,233,.12);
}

/* ── Sidebar ────────────────────────────────────────────────────────────── */
.filter-sidebar { position: sticky; top: 20px; }
.sidebar-card {
  background: white;
  border-radius: 14px;
  border: 1px solid var(--border);
  padding: 16px;
  margin-bottom: 14px;
}
.sidebar-card h6 {
  font-size: .8rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .05em;
  color: var(--text-secondary);
  margin-bottom: 10px;
}
/* Category pills in sidebar */
.cat-pill {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  border-radius: 8px;
  font-size: .85rem;
  color: #475569;
  text-decoration: none;
  margin-bottom: 2px;
  transition: background .15s;
}
.cat-pill:hover { background: #f8fafc; color: var(--text-primary); }
.cat-pill.active {
  background: #eff6ff;
  color: var(--primary-dark);
  font-weight: 700;
}
.cat-pill .count-badge {
  background: #e2e8f0;
  color: var(--text-secondary);
  border-radius: 999px;
  font-size: .7rem;
  font-weight: 600;
  padding: 1px 7px;
}
.cat-pill.active .count-badge {
  background: #bae6fd;
  color: var(--primary-dark);
}
.btn-apply {
  background: var(--primary);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: .85rem;
  font-weight: 600;
  padding: 7px 16px;
  width: 100%;
  cursor: pointer;
  font-family: 'Inter', sans-serif;
}
.btn-apply:hover { background: var(--primary-dark); }

/* ── List card grid ─────────────────────────────────────────────────────── */
.list-card-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}
@media (max-width: 768px) { .list-card-grid { grid-template-columns: 1fr; } }

.list-card {
  background: white;
  border-radius: 14px;
  border: 1px solid var(--border);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  transition: transform .2s, box-shadow .2s, border-color .2s;
}
.list-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 28px rgba(0,0,0,.10);
  border-color: #bae6fd;
}
.list-card .card-img {
  height: 160px;
  object-fit: cover;
  width: 100%;
}
.list-card .img-fallback {
  height: 160px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2.5rem;
}
.list-card .card-body { padding: 14px; flex: 1; display: flex; flex-direction: column; }
.list-card .service-price {
  font-size: 1.1rem;
  font-weight: 800;
  color: var(--primary);
}

/* ── Attribute badges ───────────────────────────────────────────────────── */
.attr-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border-radius: 6px;
  padding: 2px 8px;
  font-size: .75rem;
  font-weight: 500;
  margin: 2px;
}
.attr-yes  { background: var(--success-bg); color: var(--success-text); }
.attr-no   { background: var(--danger-bg);  color: var(--danger-text); }
.attr-num  { background: #eff6ff;           color: var(--primary-dark); }

/* ── Pagination ─────────────────────────────────────────────────────────── */
.pagination .page-link {
  border-radius: 8px;
  border: 1px solid var(--border);
  color: var(--text-secondary);
  font-size: .85rem;
  padding: 6px 12px;
  margin: 0 2px;
}
.pagination .page-link:hover { background: #f0f9ff; color: var(--primary); }
.pagination .active .page-link {
  background: #eff6ff;
  border-color: var(--primary-dark);
  color: var(--primary-dark);
  font-weight: 700;
}

/* ── Detail: carousel ───────────────────────────────────────────────────── */
.detail-carousel {
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0,0,0,.10);
  margin-bottom: 24px;
}
.detail-carousel .carousel-item img {
  height: 360px;
  object-fit: cover;
  width: 100%;
}
.detail-placeholder {
  height: 280px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 5rem;
  margin-bottom: 24px;
}

/* ── Detail: section cards ──────────────────────────────────────────────── */
.detail-card {
  background: white;
  border-radius: 14px;
  border: 1px solid var(--border);
  padding: 20px;
  margin-bottom: 20px;
}
.detail-card h5 {
  font-size: 1rem;
  font-weight: 700;
  margin-bottom: 14px;
}

/* Feature grid items */
.feature-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 10px;
  background: #f8fafc;
}
.feature-item .feat-label { font-size: .75rem; color: var(--text-muted); }
.feature-item .feat-value { font-size: .88rem; font-weight: 600; color: var(--text-primary); }

/* Reviews */
.review-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: .9rem;
  font-weight: 700;
  color: white;
  flex-shrink: 0;
}

/* ── Booking panel ──────────────────────────────────────────────────────── */
.booking-panel {
  background: white;
  border-radius: 16px;
  border: 1px solid var(--border);
  box-shadow: 0 4px 20px rgba(0,0,0,.07);
  padding: 24px;
  position: sticky;
  top: 20px;
}
.booking-price {
  font-size: 1.9rem;
  font-weight: 900;
  color: var(--primary);
  letter-spacing: -0.5px;
}
.btn-book-now {
  background: var(--primary);
  color: white;
  border: none;
  border-radius: 11px;
  width: 100%;
  padding: 13px;
  font-size: .9rem;
  font-weight: 800;
  font-family: 'Inter', sans-serif;
  cursor: pointer;
  transition: background .15s;
  text-decoration: none;
  display: block;
  text-align: center;
}
.btn-book-now:hover { background: var(--primary-dark); color: white; }

/* ── Availability calendar ──────────────────────────────────────────────── */
.calendar-day {
  width: 34px; height: 34px;
  border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  font-size: .8rem;
  cursor: default;
  background: var(--bg-page);
}
.calendar-day.available  { background: var(--success-bg); color: var(--success-text); cursor: pointer; }
.calendar-day.available:hover { background: #16a34a; color: white; }
.calendar-day.unavailable { background: var(--danger-bg); color: var(--danger-text); text-decoration: line-through; }
.calendar-day.selected   { background: var(--primary); color: white; }
.calendar-day.other-month { opacity: .3; }

/* ── Breadcrumb strip ───────────────────────────────────────────────────── */
.breadcrumb-hero {
  background: #f0f9ff;
  padding: 10px 0;
  border-bottom: 1px solid #e0f2fe;
}
.breadcrumb-hero .breadcrumb-item a { color: var(--primary-dark); text-decoration: none; }
.breadcrumb-hero .breadcrumb-item.active { color: var(--text-secondary); }
```

- [ ] **Step 2: Update `templates/base.html` — add Inter font link, restyle navbar and footer**

In the `<head>` section, add the Inter font `<link>` **before** the existing Bootstrap link. Change the footer element. The full updated file:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block title %}AnyBooking{% endblock %} — AnyBooking</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css" rel="stylesheet">
  {% load static local_names %}
  <link href="{% static 'css/main.css' %}" rel="stylesheet">
  {% block extra_head %}{% endblock %}
</head>
<body>

<nav class="navbar navbar-expand-lg">
  <div class="container">
    <a class="navbar-brand" href="{% url 'home' %}">
      <span class="brand-icon"><i class="bi bi-calendar-check"></i></span>
      AnyBooking
    </a>
    <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navMain">
      <span class="navbar-toggler-icon"></span>
    </button>
    <div class="collapse navbar-collapse" id="navMain">
      <ul class="navbar-nav me-auto">
        <li class="nav-item"><a class="nav-link" href="{% url 'service_list' %}">All Services</a></li>
        {% for cat in nav_categories %}
        <li class="nav-item">
          <a class="nav-link" href="{% url 'service_list_by_category' cat.slug %}">{{ cat|local_cat_name:request }}</a>
        </li>
        {% endfor %}
        <li class="nav-item">
          <a class="nav-link" href="{% url 'booking_lookup' %}">
            <i class="bi bi-search"></i> Find My Booking
          </a>
        </li>
      </ul>

      <!-- Location indicator -->
      <div class="me-3 d-flex align-items-center">
        {% if pref_country %}
        <span class="location-badge">
          <i class="bi bi-geo-alt-fill"></i>
          {% if pref_state %}{{ pref_state.name }}, {% endif %}{{ pref_country.name }}
        </span>
        <button class="btn btn-link btn-sm text-muted p-0 ms-2 change-location-btn" style="font-size:.75rem" onclick="openLocationModal()">
          Change
        </button>
        {% else %}
        <button class="btn btn-outline-primary btn-sm py-0 px-2 change-location-btn" style="font-size:.8rem" onclick="openLocationModal()">
          <i class="bi bi-geo-alt"></i> Set Location
        </button>
        {% endif %}
      </div>

      <a href="/admin/" class="btn-admin-cta">
        <i class="bi bi-person-gear"></i> Admin
      </a>
    </div>
  </div>
</nav>

{% if messages %}
<div class="container mt-3">
  {% for msg in messages %}
  <div class="alert alert-{{ msg.tags|default:'info' }} alert-dismissible fade show">
    {{ msg }} <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
  </div>
  {% endfor %}
</div>
{% endif %}

<!-- Location preference modal -->
<div class="modal fade" id="locationModal" tabindex="-1" aria-labelledby="locationModalLabel"
     {% if show_location_modal %}data-bs-backdrop="static" data-bs-keyboard="false"{% endif %}>
  <div class="modal-dialog modal-dialog-centered">
    <div class="modal-content">
      <div class="modal-header border-0 pb-0">
        <div class="text-center w-100 pt-2">
          <div class="display-6 text-primary mb-1"><i class="bi bi-geo-alt-fill"></i></div>
          <h5 class="modal-title fw-bold" id="locationModalLabel">Where are you looking?</h5>
          <p class="text-muted small mb-0">We'll show services available in your area</p>
        </div>
      </div>
      <div class="modal-body px-4 pb-2">

        <!-- Auto-detect button -->
        <div class="text-center mb-3">
          <button type="button" class="btn btn-outline-primary btn-sm px-4" id="detectBtn" onclick="autoDetectLocation()">
            <i class="bi bi-crosshair me-1"></i> Detect my location
          </button>
          <div id="detectStatus" class="text-muted small mt-1" style="min-height:1.2em"></div>
        </div>

        <div class="text-center text-muted small mb-3">— or select manually —</div>

        <!-- Country -->
        <div class="mb-3">
          <label class="form-label fw-semibold small">Country</label>
          <select id="modal-country" class="form-select" onchange="modalLoadStates(this.value)">
            <option value="">Select a country…</option>
            {% for c in pref_countries %}
            <option value="{{ c.id }}" data-code="{{ c.code }}">{{ c.name }}</option>
            {% endfor %}
          </select>
        </div>

        <!-- State -->
        <div class="mb-3">
          <label class="form-label fw-semibold small">State / Region <span class="text-muted fw-normal">(optional)</span></label>
          <select id="modal-state" class="form-select">
            <option value="">All states</option>
          </select>
        </div>

      </div>
      <div class="modal-footer border-0 pt-0 px-4 pb-4 flex-column gap-2">
        <button type="button" class="btn btn-primary w-100 fw-semibold" onclick="saveLocationPref()">
          <i class="bi bi-check-lg me-1"></i> Confirm Location
        </button>
        {% if not show_location_modal %}
        <button type="button" class="btn btn-link text-muted w-100 btn-sm" data-bs-dismiss="modal">Cancel</button>
        {% else %}
        <button type="button" class="btn btn-link text-muted w-100 btn-sm" onclick="skipLocation()">
          Skip for now
        </button>
        {% endif %}
      </div>
    </div>
  </div>
</div>

{% block content %}{% endblock %}

<footer class="site-footer mt-5">
  <div class="container text-center">
    <p class="mb-1 small"><span class="brand-name">AnyBooking</span></p>
    <p class="mb-0" style="font-size:.78rem">
      <a href="{% url 'service_list' %}">All Services</a> &nbsp;·&nbsp;
      <a href="{% url 'booking_lookup' %}">Find My Booking</a>
    </p>
    <p class="mb-0 mt-2" style="font-size:.72rem;color:#475569">&copy; 2025 AnyBooking · Banquet Halls · Music Bands · Catering · Hotels &amp; more</p>
  </div>
</footer>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>

<script>
(function () {
  const ajaxUrl = "{% url 'location_ajax' %}";
  const setLocUrl = "{% url 'set_location' %}";
  const showOnLoad = {{ show_location_modal|yesno:"true,false" }};
  const prefCountryId = "{{ pref_country.id|default:'' }}";
  const prefStateId = "{{ pref_state.id|default:'' }}";

  function getCookie(name) {
    const v = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
    return v ? v.pop() : '';
  }

  window.modalLoadStates = async function (countryId, preselectStateId) {
    const sel = document.getElementById('modal-state');
    sel.innerHTML = '<option value="">All states</option>';
    if (!countryId) return;
    const r = await fetch(`${ajaxUrl}?kind=states&parent_id=${countryId}`);
    const d = await r.json();
    d.results.forEach(s => {
      sel.innerHTML += `<option value="${s.id}" ${s.id == preselectStateId ? 'selected' : ''}>${s.name}</option>`;
    });
  };

  document.addEventListener('DOMContentLoaded', function () {
    const modalEl = document.getElementById('locationModal');
    modalEl.addEventListener('show.bs.modal', function () {
      const countrySel = document.getElementById('modal-country');
      if (prefCountryId && !countrySel.value) {
        countrySel.value = prefCountryId;
        modalLoadStates(prefCountryId, prefStateId);
      }
      document.getElementById('detectStatus').textContent = '';
    });
    if (showOnLoad && !sessionStorage.getItem('ab_loc_skipped')) {
      new bootstrap.Modal(modalEl).show();
    }
  });

  window.openLocationModal = function () {
    const modalEl = document.getElementById('locationModal');
    (bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl)).show();
  };

  window.saveLocationPref = async function () {
    const countryId = document.getElementById('modal-country').value;
    const stateId = document.getElementById('modal-state').value;
    const fd = new FormData();
    fd.append('country_id', countryId);
    fd.append('state_id', stateId);
    fd.append('csrfmiddlewaretoken', getCookie('csrftoken'));
    await fetch(setLocUrl, { method: 'POST', body: fd });
    window.location.reload();
  };

  window.skipLocation = function () {
    sessionStorage.setItem('ab_loc_skipped', '1');
    bootstrap.Modal.getInstance(document.getElementById('locationModal'))?.hide();
  };

  window.autoDetectLocation = async function () {
    const btn = document.getElementById('detectBtn');
    const status = document.getElementById('detectStatus');
    btn.disabled = true;
    status.textContent = 'Detecting…';
    try {
      const geo = await fetch('https://ipapi.co/json/').then(r => r.json());
      const country_code = geo.country_code || '';
      const state_name = geo.region || '';
      if (!country_code) throw new Error('no country');
      const match = await fetch(
        `${ajaxUrl}?kind=match&country_code=${encodeURIComponent(country_code)}&state_name=${encodeURIComponent(state_name)}`
      ).then(r => r.json());
      if (!match.country_id) {
        status.textContent = "Your region isn't in our database yet — please select manually.";
        btn.disabled = false;
        return;
      }
      document.getElementById('modal-country').value = match.country_id;
      await modalLoadStates(match.country_id, match.state_id || '');
      status.innerHTML = `<span class="text-success"><i class="bi bi-check-circle-fill"></i> Detected: ${match.country_name}${match.state_name ? ', ' + match.state_name : ''}</span>`;
    } catch (e) {
      status.textContent = 'Detection failed — please select manually.';
    }
    btn.disabled = false;
  };
})();
</script>

{% block extra_js %}{% endblock %}
</body>
</html>
```

- [ ] **Step 3: Run tests to confirm no regressions**

```bash
cd /path/to/project
python manage.py test --keepdb 2>&1
```

Expected: all tests pass (6 tests, 0 failures).

- [ ] **Step 4: Commit**

```bash
git add static/css/main.css templates/base.html
git commit -m "style: redesign CSS system with Inter font + navy/sky-blue tokens"
```

---

## Task 2: Home Page Redesign

**Files:**
- Modify: `templates/home.html` (full rewrite)

**Context:** The home page view (`services/views.py`) passes these context variables:
- `categories` — queryset of Category objects with `.slug`, `.icon`, `.filtered_count`, and local name via `{{ cat|local_cat_name:request }}`
- `featured` — queryset of Service objects (featured=True)
- `featured_cities` — queryset of City objects with optional `.image`

The category gradient CSS class mapping used below (`cat-bg-banquet`, `cat-bg-music`, etc.) was defined in Task 1's `main.css`. The fallback for unknown category slugs is `cat-bg-default`.

Category slug → CSS class mapping:
- `banquet_hall` → `cat-bg-banquet`
- `music_band` → `cat-bg-music`
- `catering` → `cat-bg-catering`
- `hotels` → `cat-bg-hotels`
- `dancing` → `cat-bg-dancing`
- `priests` → `cat-bg-priests`
- `event_management` → `cat-bg-events`

Category slug → emoji mapping used for fallback icon:
- `banquet_hall` → 🏛️
- `music_band` → 🎸
- `catering` → 🍽️
- `hotels` → 🏨
- `dancing` → 💃
- `priests` → 🪔
- `event_management` → 🎪

- [ ] **Step 1: Rewrite `templates/home.html`**

```django
{% extends 'base.html' %}
{% load static local_names %}
{% block title %}Home{% endblock %}

{% block content %}

{# ── Hero ──────────────────────────────────────────────────────────────── #}
<div class="hero">
  <div class="hero-content">
    <div class="hero-eyebrow">India's Premier Event Booking Platform</div>
    <h1>Find &amp; Book the<br><span class="hero-accent">Perfect Venue</span></h1>
    <p class="hero-sub">Banquet halls, music bands, catering, hotels &amp; more — across India and beyond</p>
    <form method="get" action="{% url 'service_list' %}" class="hero-search">
      <i class="bi bi-search text-muted"></i>
      <input name="q" placeholder="Search venues, services, cities…" value="{{ request.GET.q }}" autocomplete="off">
      <button type="submit">Search</button>
    </form>
    <div class="hero-stats">
      <div>
        <div class="hero-stat-num">500+</div>
        <div class="hero-stat-label">Verified Vendors</div>
      </div>
      <div>
        <div class="hero-stat-num">15+</div>
        <div class="hero-stat-label">Service Categories</div>
      </div>
      <div>
        <div class="hero-stat-num">50+</div>
        <div class="hero-stat-label">Cities Covered</div>
      </div>
    </div>
  </div>
</div>

{# ── Browse by Category ────────────────────────────────────────────────── #}
<section class="container my-5">
  <div class="d-flex align-items-center justify-content-between mb-3">
    <h2 class="section-title mb-0">Browse by Category</h2>
  </div>
  <div class="cat-grid">
    {% for cat in categories %}
    <a href="{% url 'service_list_by_category' cat.slug %}" class="cat-tile">
      <div class="cat-tile-bg
        {% if cat.slug == 'banquet_hall' %}cat-bg-banquet
        {% elif cat.slug == 'music_band' %}cat-bg-music
        {% elif cat.slug == 'catering' %}cat-bg-catering
        {% elif cat.slug == 'hotels' %}cat-bg-hotels
        {% elif cat.slug == 'dancing' %}cat-bg-dancing
        {% elif cat.slug == 'priests' %}cat-bg-priests
        {% elif cat.slug == 'event_management' %}cat-bg-events
        {% else %}cat-bg-default{% endif %}">
        {% if cat.slug == 'banquet_hall' %}🏛️
        {% elif cat.slug == 'music_band' %}🎸
        {% elif cat.slug == 'catering' %}🍽️
        {% elif cat.slug == 'hotels' %}🏨
        {% elif cat.slug == 'dancing' %}💃
        {% elif cat.slug == 'priests' %}🪔
        {% elif cat.slug == 'event_management' %}🎪
        {% else %}<i class="bi {{ cat.icon }} text-white"></i>{% endif %}
      </div>
      <div class="cat-tile-overlay">
        <div class="cat-tile-name">{{ cat|local_cat_name:request }}</div>
        <div class="cat-tile-count">{{ cat.filtered_count }} listing{{ cat.filtered_count|pluralize }}</div>
      </div>
    </a>
    {% empty %}
    <p class="text-muted">No categories configured yet. <a href="/admin/">Add via admin</a>.</p>
    {% endfor %}
    {% if categories %}
    <a href="{% url 'service_list' %}" class="cat-tile-viewall">
      <i class="bi bi-grid fs-4"></i>
      <span>View All</span>
    </a>
    {% endif %}
  </div>
</section>

{# ── Featured Listings ─────────────────────────────────────────────────── #}
{% if featured %}
<section class="container my-5">
  <div class="d-flex align-items-center justify-content-between mb-3">
    <h2 class="section-title mb-0">Featured Services</h2>
    <a href="{% url 'service_list' %}" class="btn-view">View all →</a>
  </div>
  <div class="row g-4">
    {% for svc in featured %}
    <div class="col-sm-6 col-lg-4">
      {% include 'partials/service_card.html' with service=svc %}
    </div>
    {% endfor %}
  </div>
</section>
{% endif %}

{# ── Explore by City ───────────────────────────────────────────────────── #}
{% if featured_cities %}
<div class="city-strip">
  <div class="container">
    <h2 class="section-title mb-4">Explore by City</h2>
    <div class="city-grid">
      {% for city in featured_cities %}
      <a href="{% url 'service_list' %}?city={{ city.id }}" class="city-card">
        {% if city.image %}
          <img src="{{ city.image.url }}" alt="{{ city.name }}" class="city-card-bg">
        {% else %}
          <div class="city-card-bg"></div>
        {% endif %}
        <div class="city-card-overlay">
          <span class="city-card-name">{{ city.name }}</span>
        </div>
      </a>
      {% endfor %}
    </div>
  </div>
</div>
{% endif %}

{# ── Benefits strip ────────────────────────────────────────────────────── #}
<div class="benefit-strip">
  <div class="container">
    <div class="row g-4">
      <div class="col-md-3 benefit">
        <div class="benefit-icon-box"><i class="bi bi-patch-check-fill"></i></div>
        <h5>Verified Vendors</h5>
        <p>Every vendor is reviewed before going live</p>
      </div>
      <div class="col-md-3 benefit">
        <div class="benefit-icon-box"><i class="bi bi-shield-lock-fill"></i></div>
        <h5>Secure Payments</h5>
        <p>Razorpay-backed advance — safe &amp; instant</p>
      </div>
      <div class="col-md-3 benefit">
        <div class="benefit-icon-box"><i class="bi bi-calendar2-check-fill"></i></div>
        <h5>Real Availability</h5>
        <p>Live calendar — no double-bookings, ever</p>
      </div>
      <div class="col-md-3 benefit">
        <div class="benefit-icon-box"><i class="bi bi-headset"></i></div>
        <h5>Dedicated Support</h5>
        <p>We're with you from browse to event day</p>
      </div>
    </div>
  </div>
</div>

{% endblock %}
```

- [ ] **Step 2: Run tests**

```bash
python manage.py test --keepdb 2>&1
```

Expected: all tests pass.

- [ ] **Step 3: Commit**

```bash
git add templates/home.html
git commit -m "style: redesign home page — gradient hero, category grid, city strip, benefits"
```

---

## Task 3: Service Card Partial

**Files:**
- Modify: `templates/partials/service_card.html` (full rewrite)

**Context:** This partial is included in both `home.html` (featured grid) and `services/list.html` (results grid). It receives `service` as context. The CSS classes `service-card`, `badge-category`, `badge-featured`, `attr-badge`, `attr-yes`, `attr-no`, `attr-num`, `service-price`, `btn-view` are all defined in `main.css` from Task 1.

The category gradient CSS class logic (same slug→class mapping as Task 2) is needed for the image fallback `<div>`.

- [ ] **Step 1: Rewrite `templates/partials/service_card.html`**

```django
{% load static local_names %}
<div class="service-card position-relative">
  {% if service.is_featured %}
    <span class="badge-featured">
      <i class="bi bi-star-fill"></i> Featured
    </span>
  {% endif %}

  {% with img=service.primary_image %}
    {% if img %}
      <img src="{{ img.image.url }}" class="card-img-top" alt="{{ service.name }}">
    {% else %}
      <div class="img-placeholder
        {% if service.category.slug == 'banquet_hall' %}cat-bg-banquet
        {% elif service.category.slug == 'music_band' %}cat-bg-music
        {% elif service.category.slug == 'catering' %}cat-bg-catering
        {% elif service.category.slug == 'hotels' %}cat-bg-hotels
        {% elif service.category.slug == 'dancing' %}cat-bg-dancing
        {% elif service.category.slug == 'priests' %}cat-bg-priests
        {% elif service.category.slug == 'event_management' %}cat-bg-events
        {% else %}cat-bg-default{% endif %}">
        {% if service.category.slug == 'banquet_hall' %}🏛️
        {% elif service.category.slug == 'music_band' %}🎸
        {% elif service.category.slug == 'catering' %}🍽️
        {% elif service.category.slug == 'hotels' %}🏨
        {% elif service.category.slug == 'dancing' %}💃
        {% elif service.category.slug == 'priests' %}🪔
        {% elif service.category.slug == 'event_management' %}🎪
        {% else %}<i class="bi {{ service.category.icon }} text-white fs-2"></i>{% endif %}
      </div>
    {% endif %}
  {% endwith %}

  <div class="card-body">
    <div class="d-flex align-items-center gap-2 mb-2">
      <span class="badge-category">{% service_cat_name service.category %}</span>
      {% if service.city %}
        <span class="text-muted" style="font-size:.75rem"><i class="bi bi-geo-alt"></i> {{ service.city.name }}</span>
      {% endif %}
    </div>

    <h6 class="fw-bold mb-1" style="font-size:.92rem;color:#0f172a">{{ service.name }}</h6>
    <p class="mb-2" style="font-size:.78rem;color:#64748b">{{ service.vendor.name }}</p>

    <div class="mb-2">
      {% for av in service.attribute_values.all|slice:":3" %}
        {% if av.attribute.data_type == 'boolean' %}
          <span class="attr-badge {% if av.value_boolean %}attr-yes{% else %}attr-no{% endif %}">
            <i class="bi {% if av.value_boolean %}bi-check-circle{% else %}bi-x-circle{% endif %}"></i>
            {{ av.attribute|local_attr_name:request }}
          </span>
        {% elif av.attribute.data_type == 'number' and av.value_number %}
          <span class="attr-badge attr-num">
            <i class="bi bi-people"></i> {{ av.value_number|floatformat:0 }}
          </span>
        {% endif %}
      {% endfor %}
    </div>

    {% if service.avg_rating %}
    <div class="mb-2" style="font-size:.8rem">
      <span style="color:#f59e0b"><i class="bi bi-star-fill"></i> {{ service.avg_rating|floatformat:1 }}</span>
      <span class="text-muted">({{ service.review_count }})</span>
    </div>
    {% endif %}

    <div class="mt-auto d-flex align-items-center justify-content-between">
      {% if service.base_price %}
        <div>
          <span class="service-price">{{ service.currency_symbol }}{{ service.base_price|floatformat:0 }}</span>
          <span class="text-muted" style="font-size:.75rem"> / {{ service.price_unit }}</span>
        </div>
      {% else %}
        <span class="text-muted" style="font-size:.8rem">Price on request</span>
      {% endif %}
      <a href="{% url 'service_detail' service.slug %}" class="btn-view">View →</a>
    </div>
  </div>
</div>
```

- [ ] **Step 2: Run tests**

```bash
python manage.py test --keepdb 2>&1
```

Expected: all tests pass.

- [ ] **Step 3: Commit**

```bash
git add templates/partials/service_card.html
git commit -m "style: redesign service card partial — photo-first, gradient fallback, new chips"
```

---

## Task 4: Service List Page

**Files:**
- Modify: `templates/services/list.html` (full rewrite)

**Context:** The list view passes:
- `category` — Category object or None
- `categories` — all categories (for sidebar pills)
- `services` — filtered queryset
- `q`, `sort`, `hall_type`, `min_capacity` — filter values
- `countries`, `states`, `districts`, `cities` — location dropdowns
- `selected_country`, `selected_state`, `selected_district`, `selected_city` — selected IDs as strings

The category gradient/emoji logic is the same as in Tasks 2 and 3.

- [ ] **Step 1: Rewrite `templates/services/list.html`**

```django
{% extends 'base.html' %}
{% load local_names %}
{% block title %}{% if category %}{{ category|local_cat_name:request }}{% else %}All Services{% endif %}{% endblock %}

{% block content %}

{# ── Page header ───────────────────────────────────────────────────────── #}
<div class="list-header">
  <div class="container">
    <nav aria-label="breadcrumb" class="mb-2">
      <ol class="breadcrumb mb-0" style="font-size:.8rem">
        <li class="breadcrumb-item"><a href="{% url 'home' %}" style="color:#7dd3fc;text-decoration:none">Home</a></li>
        {% if category %}
          <li class="breadcrumb-item"><a href="{% url 'service_list' %}" style="color:#7dd3fc;text-decoration:none">Services</a></li>
          <li class="breadcrumb-item active" style="color:rgba(255,255,255,.65)">{{ category|local_cat_name:request }}</li>
        {% else %}
          <li class="breadcrumb-item active" style="color:rgba(255,255,255,.65)">All Services</li>
        {% endif %}
      </ol>
    </nav>
    <h1 class="list-header-title">
      {% if category %}
        {% if category.slug == 'banquet_hall' %}🏛️
        {% elif category.slug == 'music_band' %}🎸
        {% elif category.slug == 'catering' %}🍽️
        {% elif category.slug == 'hotels' %}🏨
        {% elif category.slug == 'dancing' %}💃
        {% elif category.slug == 'priests' %}🪔
        {% elif category.slug == 'event_management' %}🎪
        {% endif %}
        {{ category|local_cat_name:request }}
      {% else %}
        All Services
      {% endif %}
    </h1>
    <p class="list-sub mb-0">{{ services.count }} result{{ services.count|pluralize }} found</p>
  </div>
</div>

{# ── Search strip ──────────────────────────────────────────────────────── #}
<div class="search-strip">
  <div class="container">
    <form method="get" id="filter-form" class="d-flex flex-wrap gap-2 align-items-center">
      {% if category %}<input type="hidden" name="category" value="{{ category.slug }}">{% endif %}
      <input name="q" class="form-control" style="max-width:220px" placeholder="Search…" value="{{ q }}">
      <select name="district" id="f-district" class="form-select" style="max-width:160px" onchange="filterCities(this.value)">
        <option value="">All Districts</option>
        {% for d in districts %}
        <option value="{{ d.id }}" {% if selected_district == d.id|stringformat:"s" %}selected{% endif %}>{{ d.name }}</option>
        {% endfor %}
      </select>
      <select name="city" id="f-city" class="form-select" style="max-width:160px">
        <option value="">All Cities</option>
        {% for c in cities %}
        <option value="{{ c.id }}" {% if selected_city == c.id|stringformat:"s" %}selected{% endif %}>{{ c.name }}</option>
        {% endfor %}
      </select>
      {% if category and category.slug == 'banquet_hall' %}
      <select name="hall_type" class="form-select" style="max-width:140px">
        <option value="">Any Type</option>
        <option value="ac" {% if hall_type == 'ac' %}selected{% endif %}>AC Hall</option>
        <option value="non_ac" {% if hall_type == 'non_ac' %}selected{% endif %}>Non AC</option>
      </select>
      {% endif %}
      <select name="sort" class="form-select" style="max-width:160px">
        <option value="">Relevance</option>
        <option value="price_asc" {% if sort == 'price_asc' %}selected{% endif %}>Price ↑</option>
        <option value="price_desc" {% if sort == 'price_desc' %}selected{% endif %}>Price ↓</option>
      </select>
      <button type="submit" class="btn-apply" style="width:auto;padding:7px 18px">Apply</button>
      <a href="{% if category %}{% url 'service_list_by_category' category.slug %}{% else %}{% url 'service_list' %}{% endif %}"
         class="btn btn-link btn-sm text-muted p-0">Clear</a>
    </form>
  </div>
</div>

{# ── Main layout ───────────────────────────────────────────────────────── #}
<div class="container my-4">
  <div class="d-flex gap-4 align-items-start">

    {# Sidebar #}
    <div class="filter-sidebar d-none d-lg-block" style="width:230px;flex-shrink:0">

      {# Categories pill list #}
      <div class="sidebar-card">
        <h6>Categories</h6>
        <a href="{% url 'service_list' %}"
           class="cat-pill {% if not category %}active{% endif %}">
          All
          <span class="count-badge">{{ services.count }}</span>
        </a>
        {% for cat in categories %}
        <a href="{% url 'service_list_by_category' cat.slug %}"
           class="cat-pill {% if category and category.slug == cat.slug %}active{% endif %}">
          {{ cat|local_cat_name:request }}
          <span class="count-badge">{{ cat.filtered_count }}</span>
        </a>
        {% endfor %}
      </div>

      {# Capacity/price filter (banquet hall only) #}
      {% if category and category.slug == 'banquet_hall' %}
      <div class="sidebar-card">
        <h6>Capacity</h6>
        <form method="get">
          {% if category %}<input type="hidden" name="category" value="{{ category.slug }}">{% endif %}
          <input type="hidden" name="q" value="{{ q }}">
          <div class="d-flex gap-2 mb-2">
            <input type="number" name="min_capacity" class="form-control form-control-sm"
                   placeholder="Min" value="{{ min_capacity }}" style="border:1.5px solid #e2e8f0;border-radius:9px">
          </div>
          <button type="submit" class="btn-apply">Apply</button>
        </form>
      </div>
      {% endif %}

    </div>

    {# Results #}
    <div style="flex:1;min-width:0">
      {% if services %}
      <div class="list-card-grid">
        {% for svc in services %}
        <div class="list-card position-relative">
          {% if svc.is_featured %}
            <span class="badge-featured">⭐ Featured</span>
          {% endif %}

          {% with img=svc.primary_image %}
            {% if img %}
              <img src="{{ img.image.url }}" class="card-img" alt="{{ svc.name }}">
            {% else %}
              <div class="img-fallback
                {% if svc.category.slug == 'banquet_hall' %}cat-bg-banquet
                {% elif svc.category.slug == 'music_band' %}cat-bg-music
                {% elif svc.category.slug == 'catering' %}cat-bg-catering
                {% elif svc.category.slug == 'hotels' %}cat-bg-hotels
                {% elif svc.category.slug == 'dancing' %}cat-bg-dancing
                {% elif svc.category.slug == 'priests' %}cat-bg-priests
                {% elif svc.category.slug == 'event_management' %}cat-bg-events
                {% else %}cat-bg-default{% endif %}">
                {% if svc.category.slug == 'banquet_hall' %}🏛️
                {% elif svc.category.slug == 'music_band' %}🎸
                {% elif svc.category.slug == 'catering' %}🍽️
                {% elif svc.category.slug == 'hotels' %}🏨
                {% elif svc.category.slug == 'dancing' %}💃
                {% elif svc.category.slug == 'priests' %}🪔
                {% elif svc.category.slug == 'event_management' %}🎪
                {% else %}<i class="bi {{ svc.category.icon }} text-white fs-2"></i>{% endif %}
              </div>
            {% endif %}
          {% endwith %}

          <div class="card-body">
            <div class="d-flex align-items-center gap-2 mb-1">
              <span class="badge-category">{{ svc.category|local_cat_name:request }}</span>
              {% if svc.city %}
                <span class="text-muted" style="font-size:.73rem"><i class="bi bi-geo-alt"></i> {{ svc.city.name }}</span>
              {% endif %}
            </div>
            <h6 class="fw-bold mb-1" style="font-size:.9rem;color:#0f172a">{{ svc.name }}</h6>
            <p class="mb-2" style="font-size:.77rem;color:#64748b">{{ svc.vendor.name }}</p>

            <div class="mb-2">
              {% for av in svc.attribute_values.all|slice:":3" %}
                {% if av.attribute.data_type == 'boolean' %}
                  <span class="attr-badge {% if av.value_boolean %}attr-yes{% else %}attr-no{% endif %}">
                    <i class="bi {% if av.value_boolean %}bi-check-circle{% else %}bi-x-circle{% endif %}"></i>
                    {{ av.attribute|local_attr_name:request }}
                  </span>
                {% elif av.attribute.data_type == 'number' and av.value_number %}
                  <span class="attr-badge attr-num">
                    <i class="bi bi-people"></i> {{ av.value_number|floatformat:0 }}
                  </span>
                {% endif %}
              {% endfor %}
            </div>

            {% if svc.avg_rating %}
            <div class="mb-2" style="font-size:.78rem">
              <span style="color:#f59e0b"><i class="bi bi-star-fill"></i> {{ svc.avg_rating|floatformat:1 }}</span>
              <span class="text-muted">({{ svc.review_count }})</span>
            </div>
            {% endif %}

            <div class="mt-auto d-flex align-items-center justify-content-between">
              {% if svc.base_price %}
                <div>
                  <span class="service-price">{{ svc.currency_symbol }}{{ svc.base_price|floatformat:0 }}</span>
                  <span class="text-muted" style="font-size:.73rem"> / {{ svc.price_unit }}</span>
                </div>
              {% else %}
                <span class="text-muted" style="font-size:.8rem">Price on request</span>
              {% endif %}
              <a href="{% url 'service_detail' svc.slug %}" class="btn-view">View →</a>
            </div>
          </div>
        </div>
        {% endfor %}
      </div>
      {% else %}
      <div class="text-center py-5 text-muted">
        <i class="bi bi-search display-4 d-block mb-3"></i>
        <h5>No services found</h5>
        <p>Try adjusting your filters or <a href="{% url 'service_list' %}">view all services</a>.</p>
      </div>
      {% endif %}
    </div>

  </div>
</div>

{% endblock %}

{% block extra_js %}
<script>
const ajaxUrl = "{% url 'location_ajax' %}";
async function loadOpts(kind, parentId, targetId, label) {
  const sel = document.getElementById(targetId);
  const cur = sel.value;
  sel.innerHTML = `<option value="">All ${label}</option>`;
  if (!parentId) return;
  const r = await fetch(`${ajaxUrl}?kind=${kind}&parent_id=${parentId}`);
  const d = await r.json();
  d.results.forEach(i => {
    sel.innerHTML += `<option value="${i.id}" ${i.id == cur ? 'selected' : ''}>${i.name}</option>`;
  });
}
function filterCities(id) { loadOpts('cities', id, 'f-city', 'Cities'); }
</script>
{% endblock %}
```

- [ ] **Step 2: Run tests**

```bash
python manage.py test --keepdb 2>&1
```

Expected: all tests pass.

- [ ] **Step 3: Commit**

```bash
git add templates/services/list.html
git commit -m "style: redesign service list page — navy header, sidebar pills, 2-col card grid"
```

---

## Task 5: Service Detail Page

**Files:**
- Modify: `templates/services/detail.html` (full rewrite)

**Context:** The detail view passes:
- `service` — Service object with `.name`, `.slug`, `.category`, `.vendor`, `.city`, `.base_price`, `.currency_symbol`, `.price_unit`, `.address`, `.pin_code`, `.description`, `.is_featured`, `.avg_rating`, `.review_count`
- `images` — queryset of ServiceImage objects (`.image.url`, `.caption`)
- `attr_values` — queryset of AttributeValue objects (`.attribute`, `.attribute.data_type`, `.value_boolean`, `.value_number`, `.display_value`)
- `reviews` — queryset of Review objects (`.reviewer_name`, `.rating`, `.created_at`, `.body`)
- `review_form` — ReviewForm instance
- `unavailable_dates` — JSON-safe list of ISO date strings for the calendar JS

Avatar colours cycle through a list based on the reviewer name's first character. Use the list: `['#0ea5e9','#0369a1','#f59e0b','#16a34a','#7c3aed','#dc2626']` with index `forloop.counter0|divisibleby` — Django's `|add` and `|divisibleby` filters can achieve this as a cycle using the `{% cycle %}` tag.

- [ ] **Step 1: Rewrite `templates/services/detail.html`**

```django
{% extends 'base.html' %}
{% load local_names %}
{% block title %}{{ service.name }}{% endblock %}

{% block content %}
<div class="breadcrumb-hero">
  <div class="container">
    <nav aria-label="breadcrumb">
      <ol class="breadcrumb mb-0 small">
        <li class="breadcrumb-item"><a href="{% url 'home' %}">Home</a></li>
        <li class="breadcrumb-item"><a href="{% url 'service_list_by_category' service.category.slug %}">{% service_cat_name service.category %}</a></li>
        <li class="breadcrumb-item active">{{ service.name }}</li>
      </ol>
    </nav>
  </div>
</div>

<div class="container my-4">
  <div class="row g-4">

    {# ── Left column ──────────────────────────────────────────────────── #}
    <div class="col-lg-8">

      {# Photo gallery #}
      {% if images %}
      <div id="serviceCarousel" class="carousel slide detail-carousel" data-bs-ride="carousel">
        <div class="carousel-inner">
          {% for img in images %}
          <div class="carousel-item {% if forloop.first %}active{% endif %}">
            <img src="{{ img.image.url }}" class="d-block w-100" alt="{{ img.caption }}">
            {% if img.caption %}<div class="carousel-caption d-none d-md-block"><small>{{ img.caption }}</small></div>{% endif %}
          </div>
          {% endfor %}
        </div>
        {% if images.count > 1 %}
        <button class="carousel-control-prev" type="button" data-bs-target="#serviceCarousel" data-bs-slide="prev">
          <span class="carousel-control-prev-icon"></span>
        </button>
        <button class="carousel-control-next" type="button" data-bs-target="#serviceCarousel" data-bs-slide="next">
          <span class="carousel-control-next-icon"></span>
        </button>
        {% endif %}
      </div>
      {% else %}
      <div class="detail-placeholder
        {% if service.category.slug == 'banquet_hall' %}cat-bg-banquet
        {% elif service.category.slug == 'music_band' %}cat-bg-music
        {% elif service.category.slug == 'catering' %}cat-bg-catering
        {% elif service.category.slug == 'hotels' %}cat-bg-hotels
        {% elif service.category.slug == 'dancing' %}cat-bg-dancing
        {% elif service.category.slug == 'priests' %}cat-bg-priests
        {% elif service.category.slug == 'event_management' %}cat-bg-events
        {% else %}cat-bg-default{% endif %}">
        {% if service.category.slug == 'banquet_hall' %}🏛️
        {% elif service.category.slug == 'music_band' %}🎸
        {% elif service.category.slug == 'catering' %}🍽️
        {% elif service.category.slug == 'hotels' %}🏨
        {% elif service.category.slug == 'dancing' %}💃
        {% elif service.category.slug == 'priests' %}🪔
        {% elif service.category.slug == 'event_management' %}🎪
        {% else %}<i class="bi {{ service.category.icon }} text-white"></i>{% endif %}
      </div>
      {% endif %}

      {# Title block #}
      <div class="detail-card">
        <div class="d-flex align-items-start justify-content-between gap-2 mb-2">
          <div>
            <span class="badge-category me-2">{% service_cat_name service.category %}</span>
            {% if service.is_featured %}
            <span class="badge-featured" style="position:static;display:inline-block">⭐ Featured</span>
            {% endif %}
          </div>
        </div>
        <h2 style="font-size:1.6rem;font-weight:900;letter-spacing:-0.6px;color:#0f172a;margin-bottom:6px">{{ service.name }}</h2>
        <p class="text-muted mb-2" style="font-size:.88rem">
          <i class="bi bi-shop"></i> {{ service.vendor.name }}
          {% if service.city %}
          &nbsp;·&nbsp; <i class="bi bi-geo-alt"></i>
          {{ service.city.name }}, {{ service.city.district.name }}, {{ service.city.state.name }}
          {% endif %}
        </p>
        {% if service.avg_rating %}
        <div class="d-flex align-items-center gap-2">
          <span style="color:#f59e0b">
            {% for i in "12345" %}
              {% if forloop.counter <= service.avg_rating %}
                <i class="bi bi-star-fill"></i>
              {% else %}
                <i class="bi bi-star"></i>
              {% endif %}
            {% endfor %}
          </span>
          <strong style="font-size:.9rem">{{ service.avg_rating|floatformat:1 }}</strong>
          <span class="text-muted" style="font-size:.82rem">({{ reviews|length }} review{{ reviews|length|pluralize }})</span>
        </div>
        {% endif %}
      </div>

      {# Description #}
      {% if service.description %}
      <div class="detail-card">
        <h5>About</h5>
        <p class="mb-0" style="font-size:.92rem;color:#334155">{{ service.description }}</p>
      </div>
      {% endif %}

      {# Features & Details #}
      <div class="detail-card">
        <h5>Features &amp; Details</h5>
        <div class="row g-2">
          {% for av in attr_values %}
          <div class="col-sm-6">
            <div class="feature-item">
              {% if av.attribute.data_type == 'boolean' %}
                <i class="bi {% if av.value_boolean %}bi-check-circle-fill text-success{% else %}bi-x-circle-fill text-danger{% endif %} fs-5 mt-1"></i>
              {% else %}
                <i class="bi bi-info-circle text-primary fs-5 mt-1"></i>
              {% endif %}
              <div>
                <div class="feat-label">{{ av.attribute|local_attr_name:request }}</div>
                <div class="feat-value">{{ av.display_value }}</div>
              </div>
            </div>
          </div>
          {% empty %}
          <p class="text-muted small">No features listed.</p>
          {% endfor %}
        </div>
      </div>

      {# Contact #}
      <div class="detail-card">
        <h5>Contact</h5>
        <p class="mb-1" style="font-size:.9rem"><i class="bi bi-person text-primary"></i> <strong>{{ service.vendor.name }}</strong></p>
        {% if service.vendor.phone %}
        <p class="mb-1" style="font-size:.9rem"><i class="bi bi-telephone text-primary"></i> {{ service.vendor.phone }}</p>
        {% endif %}
        {% if service.vendor.email %}
        <p class="mb-0" style="font-size:.9rem"><i class="bi bi-envelope text-primary"></i> {{ service.vendor.email }}</p>
        {% endif %}
      </div>

      {# Reviews #}
      <div class="detail-card">
        <h5>
          <i class="bi bi-star-half text-warning"></i> Reviews
          {% if service.avg_rating %}
          <span class="text-warning ms-1" style="font-size:.85rem">
            {% for i in "12345" %}
              {% if forloop.counter <= service.avg_rating %}<i class="bi bi-star-fill"></i>{% else %}<i class="bi bi-star"></i>{% endif %}
            {% endfor %}
          </span>
          <span class="text-muted fw-normal" style="font-size:.8rem">({{ reviews|length }})</span>
          {% endif %}
        </h5>

        {% if reviews %}
          {% for review in reviews %}
          <div class="d-flex gap-3 pb-3 mb-3 {% if not forloop.last %}border-bottom{% endif %}">
            <div class="review-avatar" style="background:{% cycle '#0ea5e9' '#0369a1' '#f59e0b' '#16a34a' '#7c3aed' '#dc2626' %}">
              {{ review.reviewer_name|slice:":1"|upper }}
            </div>
            <div style="flex:1">
              <div class="d-flex align-items-center gap-2 mb-1">
                <strong style="font-size:.88rem">{{ review.reviewer_name }}</strong>
                <span style="color:#f59e0b;font-size:.75rem">
                  {% for i in "12345" %}
                    {% if forloop.counter <= review.rating %}<i class="bi bi-star-fill"></i>{% else %}<i class="bi bi-star"></i>{% endif %}
                  {% endfor %}
                </span>
                <span class="text-muted" style="font-size:.75rem">{{ review.created_at|date:"N j, Y" }}</span>
              </div>
              <p class="mb-0" style="font-size:.85rem;color:#475569">{{ review.body }}</p>
            </div>
          </div>
          {% endfor %}
        {% else %}
          <p class="text-muted small">No reviews yet — be the first!</p>
        {% endif %}

        {# Leave a review form #}
        <h6 class="fw-bold mt-3 mb-3" style="font-size:.9rem">Leave a Review</h6>
        <form method="post" action="{% url 'add_review' service.slug %}">
          {% csrf_token %}
          <div class="mb-2">
            <label class="form-label small fw-semibold">Your name</label>
            {{ review_form.reviewer_name.errors }}
            <input type="text" name="reviewer_name" class="form-control form-control-sm" placeholder="Your name" required
                   style="border:1.5px solid #e2e8f0;border-radius:9px">
          </div>
          <div class="mb-2">
            <label class="form-label small fw-semibold">Rating</label>
            {{ review_form.rating.errors }}
            <div class="d-flex gap-2 align-items-center">
              {% for val in "12345" %}
              <div class="form-check form-check-inline">
                <input class="form-check-input" type="radio" name="rating" id="star{{ val }}" value="{{ val }}" required
                       style="accent-color:#0ea5e9">
                <label class="form-check-label small" for="star{{ val }}">{{ val }}★</label>
              </div>
              {% endfor %}
            </div>
          </div>
          <div class="mb-3">
            <label class="form-label small fw-semibold">Your experience</label>
            {{ review_form.body.errors }}
            <textarea name="body" class="form-control form-control-sm" rows="3"
                      placeholder="Share your experience…" required
                      style="border:1.5px solid #e2e8f0;border-radius:9px"></textarea>
          </div>
          <button type="submit" class="btn-apply" style="width:auto;padding:8px 20px">Submit Review</button>
        </form>
      </div>

    </div>

    {# ── Right: booking panel ─────────────────────────────────────────── #}
    <div class="col-lg-4">
      <div class="booking-panel">
        {% if service.base_price %}
        <div class="booking-price">{{ service.currency_symbol }}{{ service.base_price|floatformat:0 }}</div>
        <div class="text-muted mb-3" style="font-size:.82rem">{{ service.price_unit }}</div>
        {% else %}
        <div class="text-muted mb-3">Price on request</div>
        {% endif %}

        <h6 class="fw-semibold mb-2" style="font-size:.85rem"><i class="bi bi-calendar3"></i> Availability</h6>
        <div id="mini-calendar" class="mb-3" style="background:#f8fafc;border-radius:10px;padding:10px"></div>
        <div class="d-flex gap-3 small mb-4">
          <span class="d-flex align-items-center gap-1">
            <span style="width:14px;height:14px;background:#dcfce7;border-radius:3px;display:inline-block"></span> Available
          </span>
          <span class="d-flex align-items-center gap-1">
            <span style="width:14px;height:14px;background:#fee2e2;border-radius:3px;display:inline-block"></span> Booked
          </span>
        </div>

        <a href="{% url 'booking_create' service.slug %}" class="btn-book-now">
          <i class="bi bi-calendar-plus"></i> Book Now
        </a>
        <p class="text-muted text-center mt-2 mb-0" style="font-size:.78rem">No charges until confirmed</p>
      </div>
    </div>

  </div>
</div>
{% endblock %}

{% block extra_js %}
<script>
const unavailableDates = new Set({{ unavailable_dates|safe }});

function renderCalendar(year, month) {
  const cal = document.getElementById('mini-calendar');
  const now = new Date();
  const d = new Date(year, month, 1);
  const days = ['Su','Mo','Tu','We','Th','Fr','Sa'];

  let html = `<div class="d-flex justify-content-between align-items-center mb-2">
    <button class="btn btn-sm btn-outline-secondary py-0" onclick="changeMonth(-1)">‹</button>
    <strong style="font-size:.82rem">${d.toLocaleString('default',{month:'long'})} ${year}</strong>
    <button class="btn btn-sm btn-outline-secondary py-0" onclick="changeMonth(1)">›</button>
  </div>
  <div style="display:grid;grid-template-columns:repeat(7,1fr);gap:3px">`;

  days.forEach(day => { html += `<div class="text-center text-muted" style="font-size:.65rem;padding:2px">${day}</div>`; });

  const startDay = d.getDay();
  for (let i = 0; i < startDay; i++) html += '<div></div>';

  const daysInMonth = new Date(year, month + 1, 0).getDate();
  for (let day = 1; day <= daysInMonth; day++) {
    const iso = `${year}-${String(month+1).padStart(2,'0')}-${String(day).padStart(2,'0')}`;
    const isPast = new Date(year, month, day) < new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const isUnavail = unavailableDates.has(iso);
    let cls = 'calendar-day ';
    if (isPast || isUnavail) cls += 'unavailable';
    else cls += 'available';
    html += `<div class="${cls}" title="${iso}">${day}</div>`;
  }
  html += '</div>';
  cal.innerHTML = html;
}

let calYear = new Date().getFullYear();
let calMonth = new Date().getMonth();
function changeMonth(delta) {
  calMonth += delta;
  if (calMonth < 0) { calMonth = 11; calYear--; }
  if (calMonth > 11) { calMonth = 0; calYear++; }
  renderCalendar(calYear, calMonth);
}
renderCalendar(calYear, calMonth);
</script>
{% endblock %}
```

- [ ] **Step 2: Run tests**

```bash
python manage.py test --keepdb 2>&1
```

Expected: all tests pass.

- [ ] **Step 3: Commit**

```bash
git add templates/services/detail.html
git commit -m "style: redesign service detail page — restyled carousel, features grid, booking panel"
```

---

## Task 6: Django Unfold Admin

**Files:**
- Modify: `requirements.txt`
- Modify: `config/settings.py`
- Modify: `services/admin.py`
- Modify: `bookings/admin.py`
- Modify: `payments/admin.py`
- Modify: `terms/admin.py`
- Modify: `reviews/admin.py`
- Modify: `templates/admin/base_site.html`
- Modify: `templates/admin/dashboard.html`

**Context:**
- `django-unfold` replaces Django's default admin UI with a clean, modern white theme
- `"unfold"` MUST be listed BEFORE `"django.contrib.admin"` in `INSTALLED_APPS`
- Each `ModelAdmin` class must inherit from `unfold.admin.ModelAdmin` instead of `django.contrib.admin.ModelAdmin`
- The `@admin.register()` decorator and `admin.site` references still use `from django.contrib import admin`
- `templates/admin/base_site.html` must extend `unfold/base_site.html` so our custom CSS loads
- `templates/admin/dashboard.html` continues to extend `admin/base_site.html` (Unfold overrides this), so no change to the extends tag is needed; however the `{% block branding %}` and `{% block userlinks %}` in `base_site.html` must be removed (Unfold manages those via settings)
- No database migrations needed — Unfold adds no models

- [ ] **Step 1: Add `django-unfold` to `requirements.txt`**

Add this line at the end of `requirements.txt`:

```
django-unfold==0.62.0
```

(Verify the latest stable 0.x version with `pip index versions django-unfold` first; use whichever is latest in the 0.x series.)

- [ ] **Step 2: Install the package**

```bash
pip install django-unfold
```

Expected: Successfully installed django-unfold and its dependencies.

- [ ] **Step 3: Add `"unfold"` to `INSTALLED_APPS` in `config/settings.py`**

In `config/settings.py`, find `INSTALLED_APPS` and add `"unfold"` as the **first** entry, before `"django.contrib.admin"`:

```python
INSTALLED_APPS = [
    "unfold",
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

- [ ] **Step 4: Add the `UNFOLD` configuration dict to `config/settings.py`**

Add this block anywhere after `INSTALLED_APPS` in `config/settings.py`:

```python
UNFOLD = {
    "SITE_TITLE": "AnyBooking Admin",
    "SITE_HEADER": "AnyBooking",
    "SITE_SUBHEADER": "Event Booking Platform",
    "SITE_URL": "/",
    "SITE_ICON": None,
    "COLORS": {
        "primary": {
            "50": "240 249 255",
            "100": "224 242 254",
            "200": "186 230 253",
            "300": "125 211 252",
            "400": "56 189 248",
            "500": "14 165 233",
            "600": "2 132 199",
            "700": "3 105 161",
            "800": "7 89 133",
            "900": "12 74 110",
            "950": "8 47 73",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
        "navigation": [
            {
                "title": "Bookings",
                "items": [
                    {"title": "Bookings", "icon": "calendar_month", "link": "/admin/bookings/booking/"},
                    {"title": "Blocked Dates", "icon": "event_busy", "link": "/admin/bookings/blockeddate/"},
                    {"title": "Email Logs", "icon": "mail", "link": "/admin/bookings/emaillog/"},
                ],
            },
            {
                "title": "Services",
                "items": [
                    {"title": "Services", "icon": "storefront", "link": "/admin/services/service/"},
                    {"title": "Vendors", "icon": "person", "link": "/admin/services/vendor/"},
                    {"title": "Categories", "icon": "category", "link": "/admin/services/category/"},
                    {"title": "Attributes", "icon": "tune", "link": "/admin/services/attributedefinition/"},
                ],
            },
            {
                "title": "Reviews",
                "items": [
                    {"title": "Reviews", "icon": "star", "link": "/admin/reviews/review/"},
                ],
            },
            {
                "title": "Locations",
                "items": [
                    {"title": "Countries", "icon": "public", "link": "/admin/services/country/"},
                    {"title": "States", "icon": "map", "link": "/admin/services/state/"},
                    {"title": "Districts", "icon": "location_city", "link": "/admin/services/district/"},
                    {"title": "Cities", "icon": "place", "link": "/admin/services/city/"},
                ],
            },
            {
                "title": "Payments",
                "items": [
                    {"title": "Payments", "icon": "payments", "link": "/admin/payments/payment/"},
                    {"title": "Gateway Configs", "icon": "settings", "link": "/admin/payments/paymentgatewayconfig/"},
                ],
            },
            {
                "title": "Configuration",
                "items": [
                    {"title": "Terms of Use", "icon": "gavel", "link": "/admin/terms/termsofuse/"},
                    {"title": "Regional Configs", "icon": "translate", "link": "/admin/services/regionalcategoryconfig/"},
                    {"title": "Staff Profiles", "icon": "badge", "link": "/admin/services/staffprofile/"},
                ],
            },
            {
                "title": "Users",
                "items": [
                    {"title": "Users", "icon": "manage_accounts", "link": "/admin/auth/user/"},
                    {"title": "Groups", "icon": "group", "link": "/admin/auth/group/"},
                ],
            },
        ],
    },
}
```

- [ ] **Step 5: Update `services/admin.py` — add Unfold ModelAdmin import**

At the top of `services/admin.py`, add the unfold import after the existing django import:

```python
from unfold.admin import ModelAdmin
```

Then change every class definition that inherits from `admin.ModelAdmin` or `ModelAdmin` to inherit from the unfold `ModelAdmin`. For example:

```python
# Before:
class VendorAdmin(admin.ModelAdmin):
# After:
class VendorAdmin(ModelAdmin):
```

Do this for ALL ModelAdmin subclasses in the file. The `@admin.register(...)` decorator lines stay unchanged.

- [ ] **Step 6: Update `bookings/admin.py` — add Unfold ModelAdmin import**

Same pattern as Step 5: add `from unfold.admin import ModelAdmin` at the top, then change all `admin.ModelAdmin` parent classes to `ModelAdmin`.

- [ ] **Step 7: Update `payments/admin.py` — add Unfold ModelAdmin import**

Same pattern: add `from unfold.admin import ModelAdmin`, change all `admin.ModelAdmin` → `ModelAdmin`.

- [ ] **Step 8: Update `terms/admin.py` — add Unfold ModelAdmin import**

Same pattern: add `from unfold.admin import ModelAdmin`, change all `admin.ModelAdmin` → `ModelAdmin`.

- [ ] **Step 9: Update `reviews/admin.py` — add Unfold ModelAdmin import**

Same pattern: add `from unfold.admin import ModelAdmin`, change all `admin.ModelAdmin` → `ModelAdmin`.

- [ ] **Step 10: Update `templates/admin/base_site.html`**

Replace the entire file with (removes old branding block — Unfold reads from UNFOLD settings):

```django
{% extends "unfold/base_site.html" %}

{% block extrahead %}
{{ block.super }}
<link rel="stylesheet" href="/static/css/admin_custom.css">
{% endblock %}
```

- [ ] **Step 11: Update `templates/admin/dashboard.html`**

The dashboard already extends `admin/base_site.html` and uses `{% block content %}`. Unfold supplies its own `admin/base_site.html` when `"unfold"` is in `INSTALLED_APPS`, so the extends tag is correct. The only needed change is to remove the `{% block content_title %}{% endblock %}` override line if it conflicts with Unfold, and ensure the Chart.js script loads properly.

Replace the `{% block extrahead %}` in `dashboard.html` to load Chart.js via `{{ block.super }}`:

The existing `{% block extrahead %}` section is already correct (`{{ block.super }}`). No changes needed here beyond what Step 10 provided.

Verify the dashboard template starts with:
```django
{% extends "admin/base_site.html" %}
{% load i18n %}
```
This is already correct — no change needed.

- [ ] **Step 12: Run `collectstatic` to ensure Unfold's static files are available**

```bash
python manage.py collectstatic --noinput 2>&1 | tail -5
```

Expected: no errors; Unfold's CSS/JS files copied.

- [ ] **Step 13: Run tests**

```bash
python manage.py test --keepdb 2>&1
```

Expected: all tests pass (Unfold is a drop-in — no view/model changes).

- [ ] **Step 14: Commit**

```bash
git add requirements.txt config/settings.py services/admin.py bookings/admin.py payments/admin.py terms/admin.py reviews/admin.py templates/admin/base_site.html
git commit -m "feat: integrate django-unfold admin theme with sky-blue branding and structured sidebar nav"
```

---

## Final Verification

After all 6 tasks are complete, verify:

1. **Home page** (`/`): gradient hero renders, category tiles show per-category gradients with emojis, featured service cards show real photos or gradient fallback, city strip shows, benefits strip shows, Inter font loads.
2. **Service list** (`/services/`): navy gradient header, sidebar pills highlight active category, 2-col card grid renders with photos/fallbacks, search strip works.
3. **Service detail** (`/services/<slug>/`): Bootstrap carousel styled with rounded corners + shadow, sticky booking panel with calendar, features grid with icons, reviews with coloured avatar initials.
4. **Admin** (`/admin/`): Unfold white sidebar layout loads, sky-blue colour scheme, navigation groups match UNFOLD config, dashboard Chart.js charts still render.

Run final tests:
```bash
python manage.py test --keepdb 2>&1
```

Expected: all tests pass.
