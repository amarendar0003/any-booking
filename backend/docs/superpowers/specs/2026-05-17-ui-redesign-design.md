# AnyBooking UI Redesign — Design Spec

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Redesign the public-facing UI (home, service list, service detail) and upgrade the Django admin to Unfold, applying a consistent Modern & Elegant brand identity throughout.

**Architecture:** CSS-only changes to public templates + `main.css`; Google Fonts CDN for Inter; `django-unfold` package for admin with theme configuration in `settings.py`. No new Django apps, no model changes, no URL changes.

**Tech Stack:** Django 5.2, Bootstrap 5, Bootstrap Icons, Inter (Google Fonts), django-unfold 0.x, vanilla JS (existing)

---

## 1. Brand Identity

| Token | Value |
|---|---|
| Primary font | Inter (Google Fonts) — weights 400 500 600 700 800 900 |
| Background | `#f8fafc` (page), `white` (cards) |
| Primary colour | `#0ea5e9` (sky-blue — buttons, links, accents) |
| Primary dark | `#0369a1` (hover states, badges) |
| Navy (hero/header) | `#0f172a` → `#1e3a5f` → `#0369a1` gradient |
| Accent (stars/featured) | `#f59e0b` (amber) |
| Text primary | `#0f172a` |
| Text secondary | `#64748b` |
| Text muted | `#94a3b8` |
| Border | `#e2e8f0` |
| Success | `#dcfce7` / `#166534` |
| Danger | `#fee2e2` / `#991b1b` |

Inter replaces the current system font stack site-wide. Loaded via a single `<link>` in `base.html`.

---

## 2. Base Template (`templates/base.html`)

- Add Inter Google Fonts `<link>` in `<head>`
- Update `<body>` font-family to `'Inter', sans-serif`
- Navbar: white background, `border-bottom: 1px solid #e2e8f0`, `box-shadow: 0 1px 4px rgba(0,0,0,.06)`, height 60px
- Brand: sky-blue icon box (`#0ea5e9`, 32px, border-radius 8px) + bold brand name
- Nav links: `#64748b`, hover `#0f172a`, font-weight 500
- Location badge: `#f0f9ff` background, `#bae6fd` border, sky-blue text, pill shape
- CTA button: `background: #0ea5e9`, border-radius 8px, font-weight 700
- Footer: `background: #0f172a` (dark navy), white brand name, muted links

---

## 3. Home Page (`templates/home.html` + `static/css/main.css`)

### Hero section
- Height 520px (360px mobile)
- Background: `linear-gradient(140deg, #0f172a 0%, #1e3a5f 55%, #0369a1 100%)` — replaces the photo background
- Eyebrow text: `#7dd3fc`, uppercase, letter-spacing 2px
- H1: white, 42px, font-weight 900, letter-spacing -1.5px, with `<span style="color:#38bdf8">` on key word
- Subtext: `rgba(255,255,255,.75)`, 16px
- Search bar: white pill, border-radius 14px, `box-shadow: 0 20px 48px rgba(0,0,0,.25)`, sky-blue Search button
- Trust stats row: 3 items (Verified Vendors · Service Categories · Cities Covered), white numbers, muted labels

### Browse by Category
- Section heading: 22px, font-weight 800, letter-spacing -0.5px
- Grid: `repeat(4, 1fr)` on md+, `repeat(2, 1fr)` on mobile
- Tiles: 140px tall, border-radius 14px, coloured gradient background per category (each category gets its own gradient — see colour map below), emoji icon centred, gradient overlay to bottom, white name + count text
- "View All" tile: `#f0f9ff` background, dashed `#bae6fd` border, sky-blue icon + label
- Hover: scale(1.03) on image, overlay shifts to navy-blue tint

**Category gradient map:**
| Category | Gradient |
|---|---|
| Banquet Hall | `#1e3a5f → #0369a1` |
| Music Band | `#14532d → #166534` |
| Catering | `#7c2d12 → #92400e` |
| Hotels | `#1e1b4b → #3730a3` |
| Dancing | `#4c1d95 → #6d28d9` |
| Priests | `#7f1d1d → #991b1b` |
| Event Management | `#064e3b → #065f46` |

### Featured Services
- Section heading same style
- Grid: `repeat(3, 1fr)` on lg, `repeat(2, 1fr)` on md, `1fr` on mobile
- Service cards: white, border-radius 16px, `box-shadow: 0 1px 4px rgba(0,0,0,.06), 0 4px 16px rgba(0,0,0,.05)`, hover lifts 4px with stronger shadow
- Card image: 180px, `object-fit: cover`; fallback: category gradient with emoji
- Category badge: `#eff6ff` bg, `#0369a1` text (colour varies by category)
- Price: 17px, font-weight 800, `#0ea5e9`
- Star rating: amber `#f59e0b`
- "View →" button: `#eff6ff` bg, `#0369a1` text; hover → solid sky-blue

### Explore by City
- `background: #f0f9ff`, top/bottom `1px solid #e0f2fe` borders
- Grid: `repeat(6, 1fr)` on lg, `repeat(3, 1fr)` on md
- City cards: 100px tall, border-radius 12px, navy gradient background, white bold city name
- Photo shown if `city.image` is set; gradient fallback otherwise
- Hover: scale(1.04) transition

### Benefits strip
- White background, top/bottom border
- 4-column grid: icon box (`#eff6ff` bg, sky-blue icon, border-radius 14px) + heading + body text

### Footer
- `background: #0f172a`
- White brand name, muted grey links, copyright

---

## 4. Service List Page (`templates/services/list.html`)

### Page header
- Narrow navy gradient banner (same gradient as hero but shorter — padding 28px 32px)
- Category emoji + name as H1 (white, 26px, font-weight 800)
- Subtitle: location + description (muted white)

### Search strip
- White bar, `border-bottom: 1px solid #e2e8f0`
- Inline: search input, district dropdown, city dropdown, hall-type dropdown, sort button (right-aligned), result count
- Inputs: `border: 1.5px solid #e2e8f0`, border-radius 9px

### Layout
- `display: flex`, sidebar + results

### Sidebar (230px, sticky)
- White cards per filter group, `border-radius 14px`, `border: 1px solid #e2e8f0`
- **Categories section:** vertical pill links — active pill `#eff6ff` bg, `#0369a1` text, font-weight 700; inactive `#475569`; count badge right-aligned
- **Capacity / Price filters:** paired min/max inputs + Apply button (`background: #0ea5e9`)
- **Hall type:** checkboxes with `accent-color: #0ea5e9`

### Service card grid
- `repeat(2, 1fr)`, gap 16px
- Cards: white, `border-radius 14px`, `border: 1px solid #e2e8f0`
- Hover: translateY(-3px), stronger shadow, `border-color: #bae6fd`
- Card image: 160px — real photo if `service.primary_image` exists, else category gradient + emoji
- Featured badge: amber, absolute top-left
- Category badge, location (muted), title, vendor name
- Attribute chips: `attr-yes` green, `attr-no` red, `attr-num` blue
- Price: 18px, font-weight 800, `#0ea5e9`
- Stars: amber
- "View →" button: solid sky-blue

### Pagination
- Pill buttons, active pill `#eff6ff` + `#0369a1` border

---

## 5. Service Detail Page (`templates/services/detail.html`)

### Photo gallery
- Keep existing Bootstrap carousel
- Restyle: border-radius 16px, `box-shadow: 0 4px 20px rgba(0,0,0,.10)`
- Placeholder: category gradient + large emoji (matches list card style)

### Title block
- Category badge + Featured badge (amber)
- H2: 26px, font-weight 900, letter-spacing -0.6px
- Vendor + location in muted text
- Star rating row: amber stars, bold rating number, muted review count + link

### Features & Details card
- White card, border-radius 14px, border
- 2-column grid of feature items: icon + label + value
- `bi-check-circle-fill` green for true booleans, `bi-x-circle-fill` red for false, `bi-info-circle` blue for numbers

### Contact card
- White card, border-radius 14px, border
- Vendor name, phone, email with icons

### Reviews card
- Aggregate star display at top
- Each review: coloured initial avatar, reviewer name, star row, date, body
- "Leave a Review" form: name input + star radio buttons + textarea + Submit button

### Booking panel (right sticky column)
- White card, `box-shadow: 0 4px 20px rgba(0,0,0,.07)`, `position: sticky; top: 20px`
- Price: 30px, font-weight 900, `#0ea5e9`
- Mini availability calendar (existing JS, restyled): `background: #f8fafc`, available days `#dcfce7`, booked `#fee2e2`
- "Book Now" button: full-width, `#0ea5e9`, border-radius 11px, 14px font, font-weight 800
- "No charges until confirmed" note in muted text

---

## 6. Admin — Unfold Theme

### Package
- Add `django-unfold` to `requirements.txt`
- Add `"unfold"` to `INSTALLED_APPS` **before** `"django.contrib.admin"`

### Theme configuration (`config/settings.py`)
Configure `UNFOLD` dict with AnyBooking branding:

```python
UNFOLD = {
    "SITE_TITLE": "AnyBooking Admin",
    "SITE_HEADER": "AnyBooking",
    "SITE_SUBHEADER": "Event Booking Platform",
    "SITE_URL": "/",
    "SITE_ICON": None,
    "COLORS": {
        "primary": {
            "50": "240 249 255",   # #f0f9ff
            "100": "224 242 254",  # #e0f2fe
            "200": "186 230 253",  # #bae6fd
            "300": "125 211 252",  # #7dd3fc
            "400": "56 189 248",   # #38bdf8
            "500": "14 165 233",   # #0ea5e9  ← main primary
            "600": "2 132 199",    # #0284c7
            "700": "3 105 161",    # #0369a1
            "800": "7 89 133",     # #075985
            "900": "12 74 110",    # #0c4a6e
            "950": "8 47 73",      # #082f49
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

### ModelAdmin updates
Each existing `ModelAdmin` class needs `from unfold.admin import ModelAdmin` replacing the standard import. No logic changes — Unfold is a drop-in replacement.

Files to update:
- `services/admin.py`
- `bookings/admin.py`
- `payments/admin.py`
- `terms/admin.py`
- `reviews/admin.py`

### Dashboard template
The existing `templates/admin/dashboard.html` and `templates/admin/base_site.html` need minor updates to use Unfold's template blocks instead of the default Django admin blocks. The Chart.js dashboard content stays identical.

### Custom admin CSS
`static/css/admin_custom.css` — keep the existing table scroll rules, remove any colour overrides (Unfold handles colours via the `COLORS` config).

---

## 7. Files Changed

| File | Change |
|---|---|
| `templates/base.html` | Add Inter font link; restyle navbar, footer |
| `templates/home.html` | New hero, category grid, service cards, city strip, benefits, footer |
| `templates/services/list.html` | Page header, search strip, sidebar pills, card grid, pagination |
| `templates/services/detail.html` | Title block, feature grid, reviews card, booking panel |
| `templates/partials/service_card.html` | Photo-first card with attribute chips and new price/star layout |
| `static/css/main.css` | Full rewrite with new design tokens |
| `templates/admin/base_site.html` | Update to Unfold template blocks |
| `templates/admin/dashboard.html` | Update to Unfold template blocks |
| `config/settings.py` | Add `UNFOLD` config dict; add `"unfold"` to `INSTALLED_APPS` |
| `requirements.txt` | Add `django-unfold` |
| `services/admin.py` | Import from `unfold.admin` |
| `bookings/admin.py` | Import from `unfold.admin` |
| `payments/admin.py` | Import from `unfold.admin` |
| `terms/admin.py` | Import from `unfold.admin` |
| `reviews/admin.py` | Import from `unfold.admin` |

---

## 8. Testing

- All existing tests pass unchanged (no model/view/URL changes)
- Manual: verify home, list, detail, booking flow render correctly
- Manual: verify admin login, changelist, change form, dashboard work with Unfold
- Manual: verify dark/light mode toggle works in Unfold (built-in)
- Responsive: check home and list pages at 375px, 768px, 1280px
