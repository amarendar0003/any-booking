# AnyBooking

A multi-region event booking platform for **Banquet Halls, Music Bands, Catering, Hotels, Dancing, Priests, and Event Management** — a Django + PostgreSQL API with a cross-platform Flutter client, deployed to Google Cloud.

---

## Features

- **7 service categories** — each with configurable attributes (AC/Non-AC, capacity, veg/non-veg, etc.)
- **Photo-forward home page** — full-width hero, category photo tiles, featured city cards, and a benefits strip; images managed entirely from the admin with no code changes
- **Location hierarchy** — Country → State → District → City with cascading dropdowns
- **Regional label overrides** — category and attribute names adapt to the local language (e.g. *Priests* → *Purohit* in Telangana)
- **Availability calendar** — real-time date picker blocks already-booked and admin-blocked dates
- **Booking flow** — customer details form, event date, guest count, special requests
- **Service ratings & reviews** — customers submit star ratings and review text on the service detail page; all submissions go into an admin moderation queue before publishing; approved reviews show on the detail page and the average star rating appears on listing cards
- **Country-based payment gateways** — feature-flagged per country; Razorpay live for India; add new gateways without touching existing code
- **Terms of Use** — feature-flagged per site and/or per service; customers must read and accept before booking; full immutable acceptance audit trail (IP, user agent, version)
- **Admin portal** — full Django admin for vendors, services, bookings, payments, regional config, and review moderation
- **Admin dashboard** — live summary of bookings, revenue, refunds, and audit log with Chart.js charts
- **Location-scoped staff** — admin users restricted to a country/state/city; superuser sees everything
- **Email workflow** — automated emails on booking submission, approval, and cancellation; full HTML templates; every email audited in Email Logs
- **Approve / Cancel with refund** — admin actions to confirm or cancel bookings with full/partial/no refund selection; customer notified by email in each case
- **Vendor booking notifications** — feature-flagged per vendor; when enabled, the service provider receives an email on confirmation and cancellation
- **Booking lookup** — customers find active bookings by confirmation number or last name + phone at `/bookings/find/`
- **Customer cancellation requests** — customers request cancellation with a reason; admin is alerted; admin processes refund via existing Cancel+Refund action
- **Excel import** — bulk-load hall listings from `.xlsx` via management command
- **Cross-platform Flutter client** — iOS and Android app consuming the same API

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 5.2, Python 3.11 |
| Database | PostgreSQL 16 (Cloud SQL in production, SQLite in dev) |
| Backend frontend | Bootstrap 5, Bootstrap Icons, vanilla JS |
| Mobile client | Flutter (iOS, Android) |
| Payments | Razorpay (India) · extensible gateway layer |
| Static files | WhiteNoise |
| Container | Docker |
| CI/CD | GitHub Actions |
| Hosting | Google Cloud Run (API), Firebase Hosting (Flutter web) |
| Image registry | Google Artifact Registry |

---

## Repository Layout

```
any-booking-flutter/
├── backend/            # Django API — see backend/CLAUDE.md for app-level conventions
│   ├── services/       # Categories, attributes, vendors, listings, location hierarchy
│   ├── reviews/        # Service ratings and review moderation
│   ├── bookings/       # Booking model, availability check, booking form, email workflow
│   ├── terms/          # Terms of Use — feature-flagged per site / per service
│   ├── payments/       # Country-based payment gateway layer
│   ├── templates/      # Admin, email, and Bootstrap 5 templates
│   ├── static/css/     # Custom styles
│   ├── config/         # Django settings, URLs, WSGI
│   ├── Dockerfile
│   ├── create_admin.sh # Create/reset a production Django admin user
│   └── DB_SCHEMA.md    # Full database schema reference
├── lib/, assets/, pubspec.yaml   # Root Flutter app — the client deployed by CI/CD
├── anybookingflutter/  # Scaffolded Flutter project, not used by deployment
├── firebase.json       # Firebase Hosting config for the Flutter web build
├── setup.sh            # One-time GCP infrastructure + secrets setup
├── scripts/
│   ├── deploy.sh       # Repeat deployments of backend + Flutter web
│   ├── stop.sh         # Stop the Cloud SQL instance to avoid idle billing
│   ├── start.sh        # Start the Cloud SQL instance back up
│   └── teardown.sh     # Remove the GCP infrastructure created by setup.sh
├── .github/workflows/  # deploy.yml — CI/CD: test → build → deploy
└── SETUP.md            # Setup, deployment, infrastructure and admin guide
```

### Django apps

| App | Responsibility |
|---|---|
| `services` | Location hierarchy, categories, attributes, vendors, service listings, context processor, template tags |
| `bookings` | Booking model, availability, booking form, confirmation numbers, email log, blocked dates |
| `payments` | Gateway abstraction layer, Razorpay integration, order/callback lifecycle |
| `terms` | Terms of Use (site-wide or per-service), TermsAcceptance audit trail |
| `config` | `settings.py`, root `urls.py`, `wsgi.py` |

---

## Data Model (summary)

```
Country → State → District → City
                                └── Vendor → Service → ServiceAttributeValue
                                                └── Booking → Payment
                                                │       └── EmailLog  (audit of all comms)
                                                ├── TermsAcceptance  (immutable sign-off record)
                                                └── Review  (rating 1-5, body, moderation status)
Category → AttributeDefinition → AttributeLocalName   (regional label overrides)
Category × Country × State → RegionalCategoryConfig   (local name, enabled attrs, price unit)
StaffProfile → User  (location scope: country / state / city)
Country → PaymentGatewayConfig  (gateway slug + is_enabled feature flag)
TermsOfUse  (site-wide or Service FK; is_active feature flag)
```

See [backend/DB_SCHEMA.md](backend/DB_SCHEMA.md) for the full table-by-table reference.

---

## Service Ratings & Reviews

Customers can rate and review services directly on the service detail page. All submissions go into a moderation queue — reviews are not published until an admin approves them.

### Customer experience

- Customers fill in their name, a star rating (1–5), and a written review on the service detail page
- After submitting they see a flash message: "Thanks! Your review is awaiting approval."
- Approved reviews appear in chronological order under the service description
- The average star rating and review count are displayed as a badge on every listing card and at the top of the detail page

### Admin workflow

| Location | What to do |
|---|---|
| **Admin → Reviews → Reviews** | See all submissions with status, rating, and reviewer |
| **Admin → Reviews → filter by status: Pending** | Find all reviews awaiting moderation |
| **Select reviews → Approve selected reviews** | Publishes them immediately on the public site |
| **Select reviews → Reject selected reviews** | Hides them permanently; review content is preserved for audit |

Review content (name, rating, body, submitted date) is **read-only** in the admin — it cannot be edited after submission. Only the status can be changed.

### No environment variables required

Reviews are fully configuration-driven. No `.env` changes or gateway credentials needed.

---

## Regional Label Overrides

Category and attribute names can be customised per country or state so users always see terminology natural to their region.

| Region | Category | Shown as |
|---|---|---|
| (default) | Priests | Priests |
| India (country-wide) | Priests | Pandit / Priest |
| Telangana | Priests | Purohit |
| Tamil Nadu | Priests | Archakar |
| Punjab | Priests | Granthi |

**Priority:** State-level → Country-level → Default English name.

Configured via **Admin → Regional Category Configs**. See [SETUP.md](SETUP.md#how-regional-label-overrides-work) for full details.

---

## Admin Dashboard

A live summary dashboard is available at `/admin/dashboard/` and is linked from a **📊 Dashboard** button that appears in the top-right corner of every admin page.

| Section | Details |
|---|---|
| **Stat cards** | Total / Confirmed / Completed / Cancelled bookings; Total order value; Advance collected; Balance outstanding; Payments captured; Refunded amount |
| **Bookings trend** | Line chart — daily booking count for the last 30 days |
| **Revenue trend** | Bar chart — total value vs advance collected per month (last 6 months) |
| **Status doughnut** | Pending / Confirmed / Completed / Cancelled breakdown |
| **Top services** | Ranked by booking count with confirmed count |
| **Upcoming events** | Next 10 confirmed bookings sorted by event date |
| **Recent bookings** | Last 15 bookings with status badges and amounts |
| **Audit log** | Last 20 admin actions (Added / Changed / Deleted) with user, object, timestamp |

The dashboard is **location-aware** — staff users see only data for their assigned region.

---

## User Roles & Access

The platform has three distinct access tiers. Each uses a separate login and sees a different slice of the system.

### Access levels

| Role | Login URL | What they can access |
|---|---|---|
| **Superuser** | `/admin/` | All locations, all admin sections including Users, Groups, and Staff Profiles |
| **Staff — City scope** | `/admin/` | Only admin records belonging to that city |
| **Staff — State scope** | `/admin/` | Only admin records belonging to any city in that state |
| **Staff — Country scope** | `/admin/` | Only admin records belonging to any city in that country |
| **Staff — no profile** | `/admin/` | Nothing (fail-safe: empty querysets) |
| **Vendor** | `/vendor/login/` | Their own listings and bookings only — no admin access |

### Creating a location-scoped staff user

Staff users access the full Django admin but are restricted to their assigned region.

1. Go to **Admin → Users → Add User** — create the account with `is_staff = True`
2. Go to **Admin → Staff Profiles → Add**
3. Select the `User`, then set `Country`, `State`, or `City` — the most specific one wins
4. Save — the user can now log in and will see only their region's data

The **Users** and **Groups** sections of the admin are hidden from non-superusers entirely.

### Creating a vendor user

Vendor users access only the vendor portal (`/vendor/…`). They do **not** need `is_staff`.

1. Go to **Admin → Services → Vendors → [vendor]**
2. Scroll to **Portal Access → "Create new login account →"**
3. Enter a username and password, click **Create account**
4. Share the credentials — the vendor logs in at `/vendor/login/`

To link an existing Django user to a vendor instead, pick them from the **User** dropdown in the same fieldset.

### Django user flags summary

| Role | `is_active` | `is_staff` | `is_superuser` | Linked to |
|---|---|---|---|---|
| Superuser | ✓ | ✓ | ✓ | — |
| Staff | ✓ | ✓ | ✗ | `StaffProfile` |
| Vendor | ✓ | ✗ | ✗ | `Vendor.user` |

---

## Email Workflow

Every booking state change triggers an email. All emails are recorded in **EmailLog** regardless of success or failure.

### Automated emails

| Trigger | Recipients | Template |
|---|---|---|
| Customer submits a booking | Customer (confirmation) | `booking_received.html` |
| Customer submits a booking | Super-admin + all area admins covering that city | `admin_notify.html` |
| Admin approves a booking | Customer | `booking_approved.html` |
| Admin approves a booking | Vendor *(if notify_on_booking enabled)* | `vendor_booking_confirmed.html` |
| Admin cancels a booking | Customer (with refund details) | `booking_cancelled.html` |
| Admin cancels a booking | Vendor *(if notify_on_booking enabled)* | `vendor_booking_cancelled.html` |
| Customer requests cancellation | Customer (acknowledgement) | `cancellation_request_customer.html` |
| Customer requests cancellation | Super-admin + area admins | `cancellation_request_admin.html` |

**Area admin resolution** — on each new booking the system finds all `StaffProfile` users whose city, state, or country scope covers the booking's location and emails each of them.

**Vendor notification** — fires only when `Vendor.notify_on_booking = True` and the vendor has a valid email address. Controlled per vendor in Admin → Vendors.

### Admin actions

| Action | What it does |
|---|---|
| **✅ Approve & notify customer** | Sets status → Confirmed; sends approval email to customer; sends confirmation to vendor if enabled |
| **❌ Cancel with refund & notify customer** | Opens a form to select Full / Partial / No Refund, enter refund amount, cancellation reason (shown to customer), and internal notes; then cancels and emails customer and vendor |

### Email Logs (Admin → Bookings → Email Logs)

Every email is stored with: type badge, recipient, linked booking, subject, HTML body preview, sent/failed status, timestamp, and the admin user who triggered it. Filterable by email type, status, and date range.

The **Booking detail page** also shows an inline email history table under the *Email Communications* section.

### Email configuration

| Setting | Dev default | Production value |
|---|---|---|
| `EMAIL_BACKEND` | `console` (prints to terminal) | `django.core.mail.backends.smtp.EmailBackend` |
| `EMAIL_HOST` | `smtp.gmail.com` | Your SMTP host |
| `EMAIL_PORT` | `587` | `587` (TLS) |
| `EMAIL_HOST_USER` | _(empty)_ | Your SMTP username |
| `EMAIL_HOST_PASSWORD` | _(empty)_ | App password / secret |
| `DEFAULT_FROM_EMAIL` | `AnyBooking <noreply@anybooking.in>` | Your from address |
| `ADMIN_NOTIFY_EMAIL` | _(empty)_ | Super-admin inbox |
| `SITE_URL` | `http://127.0.0.1:8000` | `https://your-domain.com` |

Set these in `.env` locally or in Google Secret Manager for production.

---

## Terms of Use

Terms can be required at booking time and are **feature-flagged per document** — enabling or disabling a terms document takes effect immediately without a deploy.

### Scope

| Scope | Shown when |
|---|---|
| **Site-wide** | Every booking, regardless of service |
| **Service-specific** | Only bookings for the chosen service |

Both can be active at the same time. The customer sees all applicable documents in a scrollable box and must tick a single "I have read and agree" checkbox before submitting.

### Acceptance audit trail

Every acceptance is saved as an immutable `TermsAcceptance` record containing:
- Linked booking and terms document
- Version string at the moment of signing (snapshot, unaffected by later edits)
- Customer IP address and user agent
- Timestamp

Accepted terms documents cannot be deleted from the admin (the record is protected).

### Admin

| Location | Purpose |
|---|---|
| **Admin → Terms of Use** | Create / edit terms; toggle Is Active; see acceptance count and rendered preview |
| **Admin → Terms → Terms Acceptances** | Full read-only log; searchable by customer name, email, IP |
| **Admin → Bookings → [booking detail]** | Terms Acceptances inline — see which documents were signed for each booking |

---

## Vendor Portal

Hall owners and service providers can log in to a dedicated portal to view their own listings and bookings — without access to the full admin.

### Vendor login

| URL | Description |
|---|---|
| `/vendor/login/` | Vendor sign-in page |
| `/vendor/dashboard/` | Overview — active listings, pending/confirmed booking counts, recent bookings |
| `/vendor/bookings/` | Full booking list with filter by service and status |

Vendors see **only their own data**. No cross-vendor information is accessible.

### Setting up a vendor account (admin)

1. Go to **Admin → Services → Vendors → [vendor]**
2. Scroll to the **Portal Access** section
3. Click **"Create new login account →"**
4. Enter a username and password, click **Create account**
5. Share the credentials with the vendor — they log in at `/vendor/login/`

To link an existing Django user instead, pick them from the **User** dropdown in the same section.

### What vendors can see

| Section | Details |
|---|---|
| **Dashboard** | Active listing count, pending and confirmed booking counts, last 10 bookings |
| **Bookings** | All bookings for their services — filterable by service and status; shows customer name, phone, email, event date, guest count, total amount, and status |

Vendors have read-only access. They cannot modify listings, approve bookings, or see other vendors' data.

---

## Vendor Booking Notifications

Service providers (vendors) can receive email notifications when bookings for their services are confirmed or cancelled. This is **feature-flagged per vendor** — off by default, enabled individually.

### Enabling for a vendor

1. Go to **Admin → Vendors → [vendor]**
2. Ensure the **Email** field is set to a valid address
3. Tick **Notify on Booking** (or toggle it inline from the vendor list)
4. Save — takes effect immediately for the next booking event

### What the vendor receives

| Event | Email includes |
|---|---|
| **Booking confirmed** | Customer name, phone, email; event date and time; guest count; special requests; advance paid and balance due; AnyBooking reference |
| **Booking cancelled** | Event date freed; cancellation reason; no further action required message |

Both emails are recorded in Email Logs with colour-coded type badges.

---

## Booking Lookup

Customers can find their own bookings without an account at **`/bookings/find/`** — linked from the navbar and from the post-booking confirmation page.

Only **pending** and **confirmed** bookings are returned. Cancelled and completed bookings are not shown.

### Search methods

| Method | Fields required |
|---|---|
| Confirmation number | The `AB-XXXXXXXX` code from their email |
| Name + phone | Last name (partial match) and phone number (partial match) |

### Confirmation number

Every booking is assigned a unique confirmation number (`AB-` + 8 random unambiguous characters, ~1 billion combinations) on creation. It appears:
- Prominently on the post-booking confirmation page
- In the subject line and body of all transactional emails (received, approved, cancelled)
- In the admin booking list and detail view (searchable)

---

## Customer Cancellation Requests

From the lookup results page, customers can request cancellation for any active booking via a **Request Cancellation** button. This starts an async workflow — the booking is not cancelled immediately.

### Customer flow

1. Customer finds their booking at `/bookings/find/`
2. Clicks **Request Cancellation**
3. Enters a reason (required) and submits
4. Receives an acknowledgement email; sees a success screen

Submitting a second request on the same booking shows an "already requested" screen — no duplicate requests possible.

### Admin flow

1. Admin receives an email alert with the customer's reason and a direct link to the booking in the admin panel
2. A **⚠ Requested** amber badge appears on the booking in the admin list
3. Admin filters by **Cancellation Requested = Yes** to see all pending requests
4. Processes it using the existing **❌ Cancel with refund & notify customer** action (selects refund type, enters reason, fires the cancellation email)

### Email notifications

| Trigger | Recipient | Template |
|---|---|---|
| Customer submits request | Customer | `cancellation_request_customer.html` |
| Customer submits request | Super-admin + area admins | `cancellation_request_admin.html` |

---

## Payment Gateway

Online payments are **feature-flagged per country**. When disabled for a country, bookings proceed as offline/cash — no payment gateway is invoked. When enabled, customers are redirected to the gateway checkout immediately after submitting a booking.

### Current gateways

| Gateway | Region | Status |
|---|---|---|
| Razorpay | India (UPI, Cards, Net Banking) | Live |
| Stripe | International | Stub (add credentials to activate) |
| Cashfree | India / SEA | Stub |
| Paystack | Africa | Stub |

### Getting Razorpay credentials

1. Sign up at [dashboard.razorpay.com](https://dashboard.razorpay.com/signup)
2. Test-mode API keys are available immediately — toggle to **Test Mode** (top-right), then go to **Settings → API Keys → Generate Test Key**
3. For live payments, complete Razorpay's KYC/activation flow, switch to **Live Mode**, then **Settings → API Keys → Generate Live Key**
4. Copy the **Key Id** and **Key Secret** — the secret is shown only once; store it immediately

Pass both values to `setup.sh --razorpay-key-id` / `--razorpay-key-secret` (see [SETUP.md](SETUP.md#one-time-gcp-setup)), or set them later with:

```bash
printf '%s' 'YOUR_KEY_ID' | gcloud secrets versions add RAZORPAY_KEY_ID --data-file=-
printf '%s' 'YOUR_KEY_SECRET' | gcloud secrets versions add RAZORPAY_KEY_SECRET --data-file=-
```

No webhook configuration is needed — payment verification uses an HMAC signature returned directly to the checkout callback, computed from the Key Secret (see [backend/payments/gateways/razorpay_gateway.py](backend/payments/gateways/razorpay_gateway.py)).

### Enabling payments for a country

1. Go to **Admin → Payment Gateway Configs → Add**
2. Select the **Country** (e.g. India)
3. Choose the **Gateway** (e.g. Razorpay)
4. Tick **Is Enabled**
5. Save — bookings for that country now redirect to payment after submission

### Adding a new gateway

1. Create `payments/gateways/<slug>_gateway.py` implementing `BasePaymentGateway`
2. Add it to `GATEWAY_REGISTRY` in `payments/gateways/registry.py`
3. Add the slug + label to `PaymentGatewayConfig.GATEWAY_CHOICES` in `payments/models.py`
4. Create `templates/payments/checkout_<slug>.html`
5. Store API credentials in `.env` / Secret Manager

No changes to views or booking flow are needed — the registry resolves the right gateway automatically.

---

## App Check (API client attestation)

The customer-facing `/api/` endpoints (browse services, create/look up/cancel a booking) require no user login by design, which means anyone with the base URL can call them — there's no account to gate access. **Firebase App Check** narrows that: it verifies each request came from a genuine, unmodified build of the AnyBooking app (iOS, Android, or web) rather than a script, by attaching a signed attestation token (`X-Firebase-AppCheck` header) that the backend verifies against Google's public keys. It does **not** replace rate limiting — a genuine app instance can still be scripted by its own user — but it stops off-app traffic (curl, bots, scrapers) from hitting the API directly.

Enforcement is **opt-in and off by default**: until `FIREBASE_APP_CHECK_PROJECT_NUMBER` is set on the backend, [`backend/config/app_check.py`](backend/config/app_check.py)'s middleware is a no-op, and the Flutter app ([`lib/main.dart`](lib/main.dart)) simply sends requests without the header if it can't get a token — so local dev and CI need no Firebase project.

### One-time Firebase setup (manual, in the Firebase/Google Cloud console)

`setup.sh` already enables the underlying `playintegrity.googleapis.com` and `firebaseappcheck.googleapis.com` GCP APIs — the steps below are the parts that require the Firebase console, an Apple Developer account, or reCAPTCHA, which can't be scripted.

1. Go to [console.firebase.google.com](https://console.firebase.google.com) → **Add project** → link it to the existing GCP project (e.g. `any-booking-prod`) rather than creating a new one
2. **Build → App Check** → register an app for each platform once they exist:
   - **Android**: enable the **Play Integrity API** provider; requires the app's SHA-256 signing certificate fingerprint
   - **iOS**: enable **App Attest** (requires an Apple Developer account and a real bundle ID); falls back to **DeviceCheck** on older OS versions
   - **Web**: enable the **reCAPTCHA v3** provider and copy the generated site key
3. Note the **Project number** (Project Settings → General) — this is `FIREBASE_APP_CHECK_PROJECT_NUMBER`

### Wiring it into the app

Run this after `flutter create --platforms=ios,android,web .` (see [Quick Start — Flutter Client](#quick-start--flutter-client)) so the native projects exist for FlutterFire to configure:

```bash
dart pub global activate flutterfire_cli
flutterfire configure --project=YOUR_FIREBASE_PROJECT_ID
```

This overwrites the placeholder [`lib/firebase_options.dart`](lib/firebase_options.dart) with real per-platform values. Debug builds automatically use App Check's debug provider (prints a debug token to the console to register in Firebase for emulators/simulators) instead of Play Integrity/App Attest, since those don't work on unregistered dev devices.

For the web build, pass the reCAPTCHA site key at build time:

```bash
flutter build web --dart-define=APP_CHECK_WEB_RECAPTCHA_SITE_KEY=YOUR_SITE_KEY
```

### Enabling enforcement on the backend

```bash
./scripts/deploy.sh \
  --project-id YOUR_GCP_PROJECT_ID \
  --firebase-project-number YOUR_FIREBASE_PROJECT_NUMBER \
  --app-check-recaptcha-site-key YOUR_SITE_KEY
```

This sets `FIREBASE_APP_CHECK_PROJECT_NUMBER` as a Cloud Run environment variable, which turns on enforcement, and bakes the reCAPTCHA site key into the Flutter web build. Roll out gradually — deploy the app update with App Check enabled first, confirm real traffic is attaching valid tokens, *then* turn on backend enforcement, to avoid locking out users on an older app version.

---

## Phone OTP verification (Firebase Phone Auth)

The booking form ([`lib/main.dart`](lib/main.dart), `_BookingFormPageState`) sends an SMS OTP to the customer's phone via **Firebase Phone Auth** and requires it to be verified before a booking can be submitted. It uses the same Firebase project as [App Check](#app-check-api-client-attestation) — no separate project needed — and no extra Flutter dependency setup, since `firebase_auth` is already in `pubspec.yaml`.

Like App Check, this is **dormant until Firebase is actually configured**: it's gated on the same `firebaseConfigured` check (`lib/firebase_options.dart` still holding placeholder values), so until `flutterfire configure` has run, the OTP UI doesn't render and booking works exactly as before — phone number as a plain, unverified field.

**This only gates the app's UI today, not the API.** `backend/api/views.py`'s `booking_create` still accepts `customer_phone` as an untrusted string with no server-side check that it was actually verified — see the `TODO` on that view for what closing that gap looks like (sending the Firebase ID token and verifying it server-side, same shape as `config/app_check.py`).

### One-time Firebase setup

1. **Firebase console → Build → Authentication → Sign-in method → Phone → Enable.** No separate app registration needed beyond what [App Check](#app-check-api-client-attestation) already requires.
2. **Android**: silent verification uses Play Integrity and needs the same SHA-256 signing certificate fingerprint already registered for App Check — nothing extra to do once that's in place.
3. **iOS**: silent verification needs an APNs authentication key uploaded (**Project Settings → Cloud Messaging → Apple app configuration**) and the Push Notifications capability enabled in Xcode; without it, Firebase falls back to a visible reCAPTCHA/Safari verification flow instead of a silent one.
4. **Web**: `firebase_auth`'s web plugin renders its own invisible reCAPTCHA automatically — this is separate from App Check's reCAPTCHA v3 site key, no extra config needed.
5. **Billing**: phone verification is metered per SMS. The free Spark plan has a limited daily quota shared across the whole project; move to the pay-as-you-go **Blaze plan** before relying on this for real traffic.

While developing, add test numbers under **Authentication → Sign-in method → Phone numbers for testing** (each mapped to a fixed OTP code) to verify the flow without sending real SMS or burning quota.

Nothing extra is needed to wire this into the app — the same `flutterfire configure` run described under App Check's [Wiring it into the app](#wiring-it-into-the-app) populates the real config both features read from.

---

## Android app (Firebase App Distribution)

The `android` job in [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml) builds a release APK on every push to `main` and distributes it to testers through Firebase App Distribution. It's **off by default** — every step is gated on the `FIREBASE_ANDROID_APP_ID` secret being set, so it's a no-op until you configure it.

### One-time setup

Register the Android app with Firebase — this is the same registration [App Check](#app-check-api-client-attestation) needs for its Play Integrity provider, so do it once and reuse the App ID for both:

```bash
flutter create --org com.yourcompany --platforms=android .
firebase apps:create android --package-name com.yourcompany.any_booking --project YOUR_PROJECT_ID
```

This prints the **App ID** (`1:PROJECT_NUMBER:android:HEX`), also visible at **Firebase console → Project settings → Your apps**. Create a tester group in **Firebase console → Release & Monitor → App Distribution → Testers & Groups** (or `firebase appdistribution:group:create "Testers" testers --project YOUR_PROJECT_ID`).

Add two GitHub repository secrets:

| Secret | Value |
|---|---|
| `FIREBASE_ANDROID_APP_ID` | The App ID from `firebase apps:create` |
| `FIREBASE_TESTER_GROUP` | Tester group alias (optional — defaults to `testers`) |

### What it builds

The release APK is signed with Flutter's default debug keystore, since no upload keystore is configured — that's fine for internal tester distribution via App Distribution, but **the APK is not suitable for the Play Store**, which requires real release signing. Set up a proper keystore separately before publishing there.

The build number is set automatically on every deployment, for both the Android APK and the Flutter web build, without editing `pubspec.yaml` or committing back to the repo — CI (`.github/workflows/deploy.yml`) uses `github.run_number` (GitHub's per-workflow run counter), and manual deploys (`scripts/deploy.sh`) use a UTC timestamp, both passed via `flutter build ... --build-number=...`.

---

## iOS app (TestFlight)

The `ios` job in [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml) builds a release IPA on every push to `main` and uploads it to TestFlight. Requires an active [Apple Developer Program](https://developer.apple.com/programs/) membership ($99/year). It's **off by default** — every step is gated on the `IOS_DIST_CERTIFICATE_BASE64` secret being set, so it's a no-op until you configure it.

Unlike the Android/Firebase setup, none of this is scriptable end-to-end — Apple's certificate and provisioning profile creation requires their web portal and, for the export step, macOS Keychain Access. Bundle identifier: `com.anybooking.app` (set in `ios/Runner.xcodeproj/project.pbxproj`).

### One-time setup

1. **Register the App ID** — [Apple Developer → Certificates, IDs & Profiles → Identifiers](https://developer.apple.com/account/resources/identifiers/list) → register `com.anybooking.app` as an App ID (enable any capabilities the app needs, e.g. Push Notifications, if applicable later).

2. **Create the app in App Store Connect** — [App Store Connect → Apps → +](https://appstoreconnect.apple.com/apps) → New App, using the same bundle ID.

3. **Create an App Store Connect API key** (avoids interactive 2FA in CI) — [App Store Connect → Users and Access → Integrations → App Store Connect API](https://appstoreconnect.apple.com/access/integrations/api) → generate a key with **App Manager** access. Download the `.p8` file *immediately* — Apple only lets you download it once. Note the **Key ID** and **Issuer ID** shown on that page.

4. **Create a distribution certificate** — via Xcode (Settings → Accounts → Manage Certificates → + → Apple Distribution) or the [Certificates](https://developer.apple.com/account/resources/certificates/list) page. Export it from Keychain Access as a `.p12` file with a password you choose.

5. **Create an App Store provisioning profile** — [Profiles](https://developer.apple.com/account/resources/profiles/list) → + → App Store Connect → select the `com.anybooking.app` App ID and the distribution certificate from step 4. Download the `.mobileprovision` file and note the **exact profile name** you gave it. That name is baked into `ios/Runner.xcodeproj/project.pbxproj` (`PROVISIONING_PROFILE_SPECIFIER`, Runner target's Release config) as well as the `IOS_PROVISIONING_PROFILE_NAME` secret below — if you ever rotate the profile, update both.

6. **Find your Team ID** — [Apple Developer → Membership](https://developer.apple.com/account#MembershipDetailsCard) (10-character alphanumeric string).

7. **Base64-encode the certificate and profile** for GitHub secrets:

   ```bash
   base64 -i DistributionCertificate.p12 | pbcopy   # paste into IOS_DIST_CERTIFICATE_BASE64
   base64 -i profile.mobileprovision | pbcopy        # paste into IOS_PROVISIONING_PROFILE_BASE64
   ```

Add these GitHub repository secrets:

| Secret | Value |
|---|---|
| `IOS_DIST_CERTIFICATE_BASE64` | Base64 of the exported `.p12` distribution certificate (step 7) |
| `IOS_DIST_CERTIFICATE_PASSWORD` | The password you set when exporting the `.p12` (step 4) |
| `IOS_PROVISIONING_PROFILE_BASE64` | Base64 of the `.mobileprovision` file (step 7) |
| `IOS_PROVISIONING_PROFILE_NAME` | The exact profile name from step 5 |
| `IOS_KEYCHAIN_PASSWORD` | Any throwaway password (e.g. `openssl rand -base64 32`) — protects the temporary CI keychain, never used again |
| `APPSTORE_TEAM_ID` | Your Team ID (step 6) |
| `APPSTORE_API_KEY_ID` | The Key ID from step 3 |
| `APPSTORE_API_ISSUER_ID` | The Issuer ID from step 3 |
| `APPSTORE_API_PRIVATE_KEY` | The full contents of the `.p8` file from step 3 |

### What it builds

Signs with the App Store distribution certificate and provisioning profile imported into a temporary CI keychain, builds a release IPA via `flutter build ipa`, and uploads it to App Store Connect with `xcrun altool --upload-app` authenticated via the API key (no Apple ID password or 2FA prompt in CI). New builds appear in **App Store Connect → TestFlight** typically within a few minutes, after Apple's automated processing completes — testers are notified the same way as Android: an email invitation on first access, a new-build notification afterward. Add testers in **App Store Connect → TestFlight → Internal/External Testing**.

The build number uses `github.run_number`, same as Android and web.

---

## CI/CD Pipeline

Every push to `main` triggers a GitHub Actions workflow ([`.github/workflows/deploy.yml`](.github/workflows/deploy.yml)) with three jobs — `backend` runs first, then `frontend` and `android` run in parallel:

```
push to main
  │
  ├─ backend   test    Django system checks + unit tests
  │                    (runs against a real Postgres container, not mocks)
  │            build   docker build → push to Artifact Registry (us-central1)
  │            deploy  gcloud run deploy
  │                      ├─ Cloud SQL Auth Proxy (Unix socket, no sidecar needed)
  │                      ├─ Secrets pulled from Google Secret Manager
  │                      └─ python manage.py migrate runs on container startup
  │
  ├─ frontend  build Flutter web against the deployed API URL
  │            firebase deploy --only hosting → Firebase Hosting
  │
  └─ android   build a release APK against the deployed API URL
               firebase appdistribution:distribute → testers
               (skipped unless FIREBASE_ANDROID_APP_ID is set)
```

Authentication uses **Workload Identity Federation** — no service account JSON keys stored in GitHub.

App secrets (`DATABASE_URL`, `DJANGO_SECRET_KEY`, `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `ADMIN_NOTIFY_EMAIL`, `SITE_URL`) are stored in **Google Secret Manager** and injected by Cloud Run — they never touch GitHub.

For full setup and deployment instructions, see [SETUP.md](SETUP.md).

---

## Quick Start — Backend (Local)

```bash
# 1. Clone and install
git clone https://github.com/josetonyin/any-booking.git
cd any-booking-flutter/backend
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env — set SECRET_KEY and DATABASE_URL

# 3. Migrate and create admin user
python manage.py migrate
python manage.py createsuperuser

# 4. Import sample hall data (optional — real data)
python manage.py import_halls path/to/halls.xlsx

# 5. Seed all categories + USA/Canada/UAE sample data (optional — demo data)
python manage.py seed_sample_data

# 6. Run
python manage.py runserver
```

| URL | Description |
|---|---|
| http://127.0.0.1:8000/ | Public site |
| http://127.0.0.1:8000/admin/ | Admin portal |
| http://127.0.0.1:8000/admin/dashboard/ | Admin dashboard |
| http://127.0.0.1:8000/vendor/login/ | Vendor portal login |

### Admin credentials (local dev)

```
Username: admin
Password: admin1234
```

> Change before deploying to production.

---

## Quick Start — Flutter Client

The root of this repository is the active Flutter project (targeting iOS and Android), consuming the AnyBooking API at `https://any-booking-945846133192.us-central1.run.app/api`. It reuses the logo and hero artwork from the native conversions, and currently includes the home dashboard, category and service browsing, booking lookup, and vendor sign-in surfaces.

Install Flutter, then from the repository root run:

```sh
flutter create --platforms=ios,android .
flutter pub get
flutter run
```

`flutter create` is needed once here because the local workspace did not contain generated Flutter platform folders. It preserves `lib/`, `assets/`, and `pubspec.yaml` while generating the iOS and Android runners.

For a local API, pass a compile-time override:

```sh
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000/api
```

> The `anybookingflutter/` directory is a separate, scaffolded Flutter project and is **not** used by the deployment — do not run deployment commands from there.

---

## Deployment

This project deploys the root Flutter app and the Django API to Google Cloud (Cloud Run, Cloud SQL, Artifact Registry, Firebase Hosting, GitHub Actions with Workload Identity Federation).

See [SETUP.md](SETUP.md) for the step-by-step deployment guide, infrastructure reference and required IAM roles.

---

## License

MIT
