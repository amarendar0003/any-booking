# Home Page Redesign — Design Spec

**Date:** 2026-05-16  
**Status:** Approved  
**Reference:** Tagvenue.com visual style  

---

## Overview

Redesign the AnyBooking home page from its current gradient-hero + icon-card layout to a photo-forward, image-driven design inspired by Tagvenue. The goal is to make the page feel aspirational and instantly communicate the product through photography.

---

## Page Structure (top to bottom)

### 1. Navbar
- Switch from dark-blue (`navbar-dark bg-primary`) to white (`bg-white border-bottom shadow-sm`).
- Brand, nav links, location indicator, and Admin button remain. Only the colour scheme changes.
- Text links change from white to `#555` (hover: `#1a56db`).

### 2. Hero — Full-bleed Photo
- **Image:** A static venue/event photo stored as `static/img/hero.jpg`. Committed to the repo. Admin swaps it via a code deploy (SiteSettings out of scope).
- **Overlay:** `linear-gradient(to bottom, rgba(0,0,0,.45), rgba(0,0,0,.60))` over the image.
- **Height:** `420px` on desktop, `280px` on mobile.
- **Headline:** "Find & Book the Perfect Venue" (white, 2.4rem, 800 weight).
- **Subline:** current tagline, white at 88% opacity.
- **Search pill:** White rounded container (`border-radius: 12px`) with a magnifier icon, the existing `?q=` text input, and a blue Search button. Same form action as current (`{% url 'service_list' %}`).
- The location-preference modal and its trigger button remain unchanged (moved to navbar location indicator area).

### 3. Category Tiles — Photo Grid
- **Layout:** CSS grid, `repeat(auto-fill, minmax(160px, 1fr))`, gap 14px.
- **Each tile:** 120px tall, `border-radius: 14px`, overflow hidden.
  - Background: `Category.image` if set; otherwise a solid `#e9ecef` grey background (same fallback pattern as city cards).
  - Dark gradient overlay (`linear-gradient(to top, rgba(0,0,0,.65), rgba(0,0,0,.10))`).
  - Category name (white, bold) and listing count at the bottom.
  - Hover: slight scale (`transform: scale(1.05)`) on the image.
- **Model change:** Add `image = models.ImageField(upload_to='categories/', blank=True)` to `services.Category`. Run migration. Expose in admin `fieldsets`.
- Last tile in the grid is a static "View All" tile linking to `service_list`.

### 4. Benefit Strip
- Full-width white band with top and bottom `1px solid #e9ecef` border.
- 3-column grid (stacks to 1-column on mobile).
- Icons (emoji or Bootstrap Icons), bold heading, and one-line description:
  - ✅ **Verified Listings** — Every vendor is reviewed before going live
  - 🔒 **Secure Payments** — Razorpay-backed advance — safe & instant
  - 📅 **Real Availability** — Live calendar — no double-bookings, no surprises
- Text is hardcoded in the template (not admin-editable).

### 5. Popular Cities — Photo Cards
- **Layout:** CSS grid, `repeat(auto-fill, minmax(180px, 1fr))`, gap 14px.
- **Each card:** 130px tall, `border-radius: 14px`, semi-transparent overlay (`rgba(0,0,0,.40)`), city name centred in white bold text.
- Each card links to `{% url 'service_list' %}?city=<id>`.
- **Model change:** Add two fields to `services.City`:
  - `is_featured = models.BooleanField(default=False)` — admin ticks to pin a city.
  - `image = models.ImageField(upload_to='cities/', blank=True)` — optional photo.
  - If no image is uploaded, the card shows a solid `#dee2e6` background with the city name (graceful fallback).
- **Admin:** Expose `is_featured` and `image` in the City admin. The home view queries `City.objects.filter(is_featured=True)` ordered by name, limited to 6.
- **Migration:** One migration covering both the `is_featured` and `image` fields on City.

### 6. Featured Listings
- Keep the existing `featured` queryset (services with `is_featured=True`).
- Update card styles to match the new aesthetic: white background, `border-radius: 14px`, `box-shadow`, 190px image, location + category meta line, price line.
- "View All Services" button below the grid: outlined blue, same target as current.

### 7. How It Works
- Keep the existing 4-step layout (Browse → Check Availability → Book → Pay & Confirm).
- Move to a white background section with top border (matches the benefit strip style).

### 8. Footer
- Simplify to a minimal dark footer (`#111` background): copyright + tagline only.

---

## Model Changes Summary

| Model | Field | Type | Notes |
|---|---|---|---|
| `services.Category` | `image` | `ImageField(upload_to='categories/', blank=True)` | Optional photo for category tile |
| `services.City` | `is_featured` | `BooleanField(default=False)` | Pins city to home page |
| `services.City` | `image` | `ImageField(upload_to='cities/', blank=True)` | Optional photo for city card |

Both changes go in a single migration.

---

## CSS Changes

All new styles go into `static/css/main.css`. Key additions:

- `.hero` — replace gradient with `position:relative; height:420px; overflow:hidden`
- `.hero-img` — full-cover background image
- `.hero-overlay` — absolute positioned dark gradient
- `.hero-search` — white pill search container
- `.cat-tile`, `.cat-tile-overlay` — photo tile + overlay + hover scale
- `.benefit-strip`, `.benefit` — benefit icon strip
- `.city-card`, `.city-card-overlay` — city photo card
- Navbar: remove `.navbar-dark` / `bg-primary`, add `bg-white border-bottom`

Existing `.service-card` styles are updated (not replaced) to match the new look.

---

## Hero Image

A royalty-free venue/event photo is saved as `static/img/hero.jpg` (committed to git, ~200KB optimised). The `<img>` tag in the template uses `{% static 'img/hero.jpg' %}`.

---

## Out of Scope

- SiteSettings model for admin-editable hero image
- City card ordering / drag-and-drop in admin
- Testimonials or review quotes section
- Any changes to the service list, detail, or booking pages

---

## Files Affected

| File | Change |
|---|---|
| `templates/home.html` | Full rewrite |
| `templates/base.html` | Navbar colour scheme only |
| `static/css/main.css` | Hero, category tile, city card, benefit strip, navbar, listing card styles |
| `static/img/hero.jpg` | New static asset |
| `services/models.py` | Add `Category.image`, `City.is_featured`, `City.image` |
| `services/admin.py` | Expose new fields in Category and City admin |
| `services/views.py` | Home view: add featured cities queryset |
| `services/migrations/XXXX_home_redesign.py` | New migration |
