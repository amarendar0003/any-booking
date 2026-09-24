# AnyBooking — Login / Signup / Logout Flow

## Overview

There is **one login entry point** for all normal users: the **Sign In button in the home-page navbar**, which opens the authentication modal (`backend/templates/accounts/auth_modal.html`). All auth endpoints are JSON and live in `backend/accounts/views.py` (`backend/accounts/urls.py`).

| Persona | Logs in via | Redirect after login |
|---|---|---|
| Customer | Home nav → Sign In modal (email + password) | `/` (home page) |
| Vendor | Home nav → Sign In modal (email + password) | `/vendor/dashboard/` |
| Vendor staff | Home nav → Sign In modal (email + password) | `/vendor/dashboard/` (vendor/staff portal) |
| Superuser (admin) | Django `/admin/` only | Django admin |

- The **old separate Vendor Login page is removed**. Visiting `/vendor/login/` now simply redirects to `/` (or to `/vendor/dashboard/` if already signed in as a vendor). There is no vendor username/password form anywhere on the site.
- The Django **`/admin/`** login and the DRF endpoint `POST /api/auth/vendor/login/` are unchanged.

## 1. Sign Up (first-time users) — 3 steps

### Step 1 — Name + phone + email + role → `POST /accounts/signup/` (`signup_view`)
- User opens the modal, selects **Sign Up**, enters **full name**, **phone number**, **email** and picks a role: `customer` or `vendor`.
- Validation: name and phone required; phone matched against `[0-9+\-\s()]{7,20}`.
- Creates a Django **User** with `username = email`, `first_name = name`, `is_active = False`, and **no usable password**, plus a **UserProfile** with the chosen role and the phone number.
  - **Name** is stored in the `auth_user` table (`first_name`).
  - **Phone** is stored in the `accounts_userprofile` table (`phone`).
- Generates a **5-minute OTP** (`EmailVerificationToken.generate_for_user`) and emails it via the Brevo mail service (`send_otp_email`).
- If the email belongs to an already fully-registered user, a generic "code sent" reply is returned (no account enumeration). Unverified/incomplete signups are refreshed with the new details and re-OTP'd.

### Step 2 — OTP verification → `POST /accounts/verify-email/` (`verify_email_view`)
- User submits the emailed code.
- Marks `profile.email_verified = True` and activates the user (`is_active = True`).

### Step 3 — Create password → `POST /accounts/create-password/` (`create_password_view`)
- Password is validated with Django's `validate_password`, then saved; `profile.password_set = True`.
- **Vendor role:** `_ensure_vendor_profile()` auto-creates a `services_vendor` row linked `OneToOne` to the user (`vendor_profile`) using the **name and phone captured at signup** — vendors are auto-approved.
- The user is **logged in immediately** and redirected by role (vendor → `/vendor/dashboard/`, customer → `/`).

## 2. Sign In → `POST /accounts/login/` (`login_view`)

1. Client POSTs `{ email, password }` (email lowercased).
2. `authenticate(username=email, password=...)` — works for every account because signup stores `username = email`.
3. Guards:
   - Unknown email / wrong password → `401 Invalid email or password`.
   - `is_superuser` → `403` "Please sign in from the admin console" (admins must use `/admin/`).
   - `email_verified == False` → `403` verify-your-email message.
   - `password_set == False` → `403` complete-signup message.
   - No `UserProfile` (e.g. vendor staff account created from the Django admin) → allowed through; routing is decided by role resolution.
4. `login(request, user)` creates a session (`django_session` row + `sessionid` cookie).
5. `_post_login_redirect()` returns the landing URL:
   - `UserProfile.role == 'vendor'` → `/vendor/dashboard/`
   - vendor owner/staff account (resolved via `vendors.views._resolve_vendor_role`) → `/vendor/dashboard/`
   - Django staff/superuser → `/admin/`
   - everyone else (customer) → `/`

## 3. Sign Out

**Customer / vendor (site navbar):**
1. Avatar dropdown → **Sign Out** button calls `navLogout()` (defined in `backend/templates/base.html`).
2. `navLogout()` reads the `csrftoken` cookie and issues `fetch('POST /accounts/logout/')`.
3. `logout_view` runs Django `logout()` — the session is deleted.
4. The browser is redirected to **`/`** (home page).

**Vendor portal:** the portal sidebar's Sign-out link hits `GET /vendor/logout/` (`vendors.views.vendor_logout_view`) → `logout()` → **redirect to `/`**.

## 4. Database tables involved

| Table | Written when | Notes |
|---|---|---|
| `auth_user` (Django) | signup step 1, password step | `username` = email, `first_name` = signup name, `password` hash, `is_active` False → True after OTP |
| `accounts_userprofile` | signup step 1, verify, password step | `role` (customer/vendor), `phone` (from signup), `email_verified`, `password_set` flags |
| `accounts_emailverificationtoken` | signup step 1, resend OTP | hashed code, 5-minute expiry, used flag |
| `accounts_passwordsetuptoken` | password-setup links (admin-invited users) | token hash + expiry |
| `services_vendor` | password step (vendor role only) | `user` OneToOne (`vendor_profile`) grants vendor-portal ownership |
| `services_vendorstaffuser` | Django admin only | `vendor` + `user` link for staff portal access |
| `django_session` | sign in / sign out | one row per session; removed on logout |

## 5. End-to-end sequence (vendor happy path)

```
Home page → Sign In → Sign Up
  POST /accounts/signup/  (name, phone, email, role=vendor)  → auth_user + accounts_userprofile + OTP email
  POST /accounts/verify-email/ (email, code)     → email_verified=True, is_active=True
  POST /accounts/create-password/ (email, pass)  → password set + services_vendor created (name/phone from signup)
                                                 → auto login → /vendor/dashboard/
…later…
  POST /accounts/login/ (email, password)        → session → /vendor/dashboard/
  navbar → Sign Out → POST /accounts/logout/     → session deleted → /
```
