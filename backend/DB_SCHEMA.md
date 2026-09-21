# AnyBooking — Database Schema

> Generated from Django models · SQLite (dev) / PostgreSQL (prod)  
> Apps: `services` · `bookings` · `payments`

---

## Entity Relationship Overview

```
Country
  └── State
        └── District
              └── City
                    ├── Vendor
                    │     └── Service ──── Category
                    │           ├── ServiceAttributeValue ── AttributeDefinition
                    │           │                                   └── AttributeLocalName
                    │           ├── ServiceImage
                    │           ├── BlockedDate
                    │           └── Booking
                    │                 └── Payment
                    └── (RegionalCategoryConfig links Category × Country × State)
```

---

## App: Services

### Country
Location hierarchy root. Holds currency and phone settings per country.

| Field | Type | Constraints / Notes |
|---|---|---|
| id | BigAutoField | PK |
| name | CharField | UNIQUE · max_length=100 |
| code | CharField | UNIQUE · max_length=5 · ISO 2-letter code, e.g. `IN` |
| currency | CharField | max_length=10 · default=`INR` |
| currency_symbol | CharField | max_length=5 · default=`₹` |
| phone_code | CharField | max_length=10 · default=`+91` |
| is_active | BooleanField | default=True |

---

### State
A state or province belonging to a country.

| Field | Type | Constraints / Notes |
|---|---|---|
| id | BigAutoField | PK |
| country_id | ForeignKey | → Country (CASCADE) |
| name | CharField | max_length=100 · UNIQUE per country |
| code | CharField | max_length=10 · blank · State/Province code |
| is_active | BooleanField | default=True |

---

### District
A district within a state.

| Field | Type | Constraints / Notes |
|---|---|---|
| id | BigAutoField | PK |
| state_id | ForeignKey | → State (CASCADE) |
| name | CharField | max_length=100 · UNIQUE per state |
| is_active | BooleanField | default=True |

---

### City
A city within a district. Services and vendors are linked here.

| Field | Type | Constraints / Notes |
|---|---|---|
| id | BigAutoField | PK |
| district_id | ForeignKey | → District (CASCADE) |
| name | CharField | max_length=100 · UNIQUE per district |
| pin_code | CharField | max_length=20 · blank |
| is_active | BooleanField | default=True |

---

### Category
One of the 7 fixed service types.

| Field | Type | Constraints / Notes |
|---|---|---|
| id | BigAutoField | PK |
| slug | SlugField | UNIQUE · choices: `banquet_hall`, `music_band`, `event_management`, `catering`, `dancing`, `priests`, `hotels` |
| description | TextField | blank |
| icon | CharField | max_length=50 · Bootstrap Icons class, e.g. `bi-building` |

---

### AttributeDefinition
A configurable property for a category (e.g. "AC Hall", "Venue Capacity").

| Field | Type | Constraints / Notes |
|---|---|---|
| id | BigAutoField | PK |
| category_id | ForeignKey | → Category (CASCADE) |
| name | CharField | max_length=100 · Default English name |
| slug | SlugField | max_length=100 · UNIQUE per category |
| data_type | CharField | choices: `boolean`, `text`, `number`, `choice` · default=`boolean` |
| choices | TextField | blank · Comma-separated options (for `choice` type) |
| unit | CharField | max_length=30 · blank · e.g. `persons`, `hours` |
| is_filterable | BooleanField | default=True · shown in search filters |
| order | PositiveSmallIntegerField | default=0 · display order |

---

### AttributeLocalName
Overrides an attribute's label for a specific country or state (e.g. "AC Hall" → "AC Mantapam" in Telangana).

| Field | Type | Constraints / Notes |
|---|---|---|
| id | BigAutoField | PK |
| attribute_id | ForeignKey | → AttributeDefinition (CASCADE) |
| country_id | ForeignKey | → Country (CASCADE) |
| state_id | ForeignKey | → State (SET_NULL) · nullable · blank = country-wide override |
| local_name | CharField | max_length=100 · Name shown to users in this region |

**Unique constraint:** `(attribute, country, state)`

---

### RegionalCategoryConfig
Per-region configuration for a category: local label, local description, active attributes, and price unit.  
State-level row overrides the country-level row automatically.

| Field | Type | Constraints / Notes |
|---|---|---|
| id | BigAutoField | PK |
| category_id | ForeignKey | → Category (CASCADE) |
| country_id | ForeignKey | → Country (CASCADE) |
| state_id | ForeignKey | → State (SET_NULL) · nullable · blank = country-wide default |
| local_display_name | CharField | max_length=100 · blank · e.g. `Purohit` instead of `Priests` in Telangana |
| local_description | TextField | blank · Description in the local language |
| price_unit_label | CharField | max_length=50 · default=`per event` · e.g. `per plate`, `per night` |
| notes | TextField | blank · Admin-only notes |
| enabled_attributes | ManyToManyField | → AttributeDefinition · Attributes active for this category in this region |

**Unique constraint:** `(category, country, state)`

---

### Vendor
A service provider (hall owner, caterer, band, etc.).

| Field | Type | Constraints / Notes |
|---|---|---|
| id | BigAutoField | PK |
| name | CharField | max_length=200 |
| email | EmailField | nullable · blank |
| phone | CharField | max_length=20 |
| address | TextField | blank |
| city_id | ForeignKey | → City (SET_NULL) · nullable |
| is_active | BooleanField | default=True |
| created_at | DateTimeField | auto_now_add |

---

### Service
A specific listing offered by a vendor (e.g. "Royal Gardens – AC Hall").

| Field | Type | Constraints / Notes |
|---|---|---|
| id | BigAutoField | PK |
| vendor_id | ForeignKey | → Vendor (CASCADE) |
| category_id | ForeignKey | → Category (PROTECT) |
| city_id | ForeignKey | → City (SET_NULL) · nullable |
| name | CharField | max_length=200 |
| slug | SlugField | UNIQUE · max_length=220 · auto-generated |
| description | TextField | blank |
| address | TextField | blank |
| pin_code | CharField | max_length=20 · blank |
| base_price | DecimalField | max_digits=12, decimal_places=2 · default=0 |
| price_unit | CharField | max_length=50 · default=`per event` |
| is_active | BooleanField | default=True |
| is_featured | BooleanField | default=False |
| created_at | DateTimeField | auto_now_add |
| updated_at | DateTimeField | auto_now |

---

### ServiceAttributeValue
Stores the value of one attribute for one service.

| Field | Type | Constraints / Notes |
|---|---|---|
| id | BigAutoField | PK |
| service_id | ForeignKey | → Service (CASCADE) |
| attribute_id | ForeignKey | → AttributeDefinition (CASCADE) |
| value_boolean | BooleanField | nullable · used when data_type=`boolean` |
| value_text | CharField | max_length=500 · blank · used when data_type=`text` or `choice` |
| value_number | DecimalField | nullable · max_digits=12 · used when data_type=`number` |

**Unique constraint:** `(service, attribute)`

---

### ServiceImage
Photos for a service listing.

| Field | Type | Constraints / Notes |
|---|---|---|
| id | BigAutoField | PK |
| service_id | ForeignKey | → Service (CASCADE) |
| image | ImageField | upload_to=`services/` |
| caption | CharField | max_length=200 · blank |
| is_primary | BooleanField | default=False |
| order | PositiveSmallIntegerField | default=0 |

---

## App: Bookings

### Booking
A customer booking request for a service.

| Field | Type | Constraints / Notes |
|---|---|---|
| id | BigAutoField | PK |
| service_id | ForeignKey | → Service (PROTECT) |
| customer_name | CharField | max_length=200 |
| customer_email | EmailField | max_length=254 |
| customer_phone | CharField | max_length=20 |
| event_date | DateField | |
| event_end_date | DateField | nullable · blank · multi-day bookings |
| event_time | TimeField | nullable · blank |
| guest_count | PositiveIntegerField | default=1 |
| special_requests | TextField | blank |
| total_amount | DecimalField | max_digits=12, decimal_places=2 |
| advance_amount | DecimalField | max_digits=12, decimal_places=2 · default=0 |
| status | CharField | max_length=20 · choices: `pending`, `confirmed`, `cancelled`, `completed` · default=`pending` |
| admin_notes | TextField | blank |
| created_at | DateTimeField | auto_now_add |
| updated_at | DateTimeField | auto_now |

---

### BlockedDate
Dates manually blocked by admin so no bookings can be made.

| Field | Type | Constraints / Notes |
|---|---|---|
| id | BigAutoField | PK |
| service_id | ForeignKey | → Service (CASCADE) |
| date | DateField | |
| reason | CharField | max_length=200 · blank |

**Unique constraint:** `(service, date)`

---

## App: Payments

### Payment
A Razorpay payment record linked to a booking.

| Field | Type | Constraints / Notes |
|---|---|---|
| id | BigAutoField | PK |
| booking_id | ForeignKey | → Booking (PROTECT) |
| razorpay_order_id | CharField | UNIQUE · max_length=100 |
| razorpay_payment_id | CharField | max_length=100 · blank · filled after capture |
| razorpay_signature | CharField | max_length=255 · blank · filled after capture |
| amount | DecimalField | max_digits=12, decimal_places=2 · in INR |
| status | CharField | max_length=20 · choices: `created`, `captured`, `failed`, `refunded` · default=`created` |
| created_at | DateTimeField | auto_now_add |
| updated_at | DateTimeField | auto_now |
