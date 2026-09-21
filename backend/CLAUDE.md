# AnyBooking — Claude Code Guide

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | Django 5.2, Python 3.11 |
| Database | PostgreSQL 16 (prod / CI), SQLite (local dev) |
| Frontend | Bootstrap 5 + Bootstrap Icons, vanilla JS |
| Payments | Razorpay (advance payment, HMAC signature verification) |
| Static files | WhiteNoise (`CompressedManifestStaticFilesStorage`) |
| Media | Pillow for image processing |
| Container | Docker (gunicorn entrypoint) |
| CI/CD | GitHub Actions → Cloud Build → Cloud Run (us-central1) |
| Auth | Workload Identity Federation — no JSON keys in GitHub |
| Secrets | Google Secret Manager |
| Database (prod) | Cloud SQL (PostgreSQL 16) |

## Django Apps

| App | Responsibility |
|---|---|
| `services` | Location hierarchy, categories, attributes, vendors, service listings, context processor, template tags |
| `bookings` | Booking model, availability, booking form, confirmation numbers, email log, blocked dates |
| `payments` | Gateway abstraction layer, Razorpay integration, order/callback lifecycle |
| `terms` | Terms of Use (site-wide or per-service), TermsAcceptance audit trail |
| `config` | `settings.py`, root `urls.py`, `wsgi.py` |

## Key Conventions

- Business logic lives in the app it belongs to. New URL patterns go in that app's `urls.py`.
- All templates are under `templates/` at project root.
- Context available to every template: `services.context_processors.nav_categories`.
- Payment gateway is fully abstracted — `payments/gateways/registry.py` → `get_gateway_for_country()`. Never import Razorpay directly outside its gateway module.
- Confirmation numbers: `AB-XXXXXXXX`, auto-generated in `Booking.save()` using `secrets.choice` over an unambiguous character set (no 0/O/1/I).
- Email sending always writes an `EmailLog` record regardless of success/failure.
- Admin access is location-scoped via `LocationRestrictedMixin` and `StaffProfile`.
- Vendor portal access (`/vendor/`) is controlled by `vendors/views.vendor_required` — checks `request.user.vendor_profile` (the `Vendor.user` OneToOneField). Vendor users need no `is_staff` flag.

## Local Development

```bash
# .env required fields
SECRET_KEY=...
DATABASE_URL=sqlite:///db.sqlite3   # or postgres://...
RAZORPAY_KEY_ID=...
RAZORPAY_KEY_SECRET=...
ADMIN_NOTIFY_EMAIL=you@example.com
DEFAULT_FROM_EMAIL=noreply@example.com
SITE_URL=http://127.0.0.1:8000

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Default local admin credentials (change before prod): `admin / admin1234`

## Testing

- Always test against **real PostgreSQL**, never SQLite or mocked DB.
- CI runs tests against an ephemeral Postgres container — keep that pattern locally too.

## Commits

- No `Co-Authored-By: Claude` trailers in commit messages.

## Deployment

- Push to `main` → GitHub Actions runs tests → builds Docker image → deploys to Cloud Run.
- Secrets are pulled from Google Secret Manager at runtime (not baked into the image).
- Use `gcloud` / GCP console for infra changes. Default region: `us-central1`.
