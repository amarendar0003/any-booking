# AnyBooking Django — Brevo Email Verification Integration Guide

## Purpose

Implement production-ready email verification for the AnyBooking Django backend using Brevo SMTP.

Current environment:
- Django backend
- PostgreSQL
- Local development now; production deployment later
- Brevo SMTP key has already been created
- Goal: every newly registered user must verify their email before creating a password / accessing the account

## Important architecture

Django owns the authentication/business logic. Brevo is only the email delivery service.

Flow:

User submits email
→ Django validates email
→ Django creates an unverified account
→ Django creates a secure, expiring verification token
→ Django sends verification email through Brevo SMTP
→ User clicks verification link
→ Django validates token
→ Django marks email as verified
→ User is allowed to create a password
→ Password is securely hashed
→ User can log in normally

Do NOT make Brevo responsible for account state or password storage.

---

# 1. Brevo configuration

Brevo SMTP configuration:

```env
BREVO_SMTP_HOST=smtp-relay.brevo.com
BREVO_SMTP_PORT=587
BREVO_SMTP_USER=<Brevo SMTP login>
BREVO_SMTP_PASSWORD=<Brevo SMTP key>
BREVO_FROM_EMAIL=<verified Brevo sender>
BREVO_FROM_NAME=AnyBooking
```

Use the SMTP key, NOT a Brevo API key.

Port 587 should use TLS.

Do not commit `.env` to Git.

Brevo's current SMTP documentation states that `smtp-relay.brevo.com` is the SMTP server, the SMTP login is the account/assigned SMTP login, and the SMTP key is the SMTP password. Brevo recommends port 587 with TLS as the default. Verify the sender/domain in Brevo before sending production mail.

---

# 2. Django settings

Use environment variables.

Example:

```python
import os

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

EMAIL_HOST = os.getenv("BREVO_SMTP_HOST")
EMAIL_PORT = int(os.getenv("BREVO_SMTP_PORT", "587"))
EMAIL_HOST_USER = os.getenv("BREVO_SMTP_USER")
EMAIL_HOST_PASSWORD = os.getenv("BREVO_SMTP_PASSWORD")
EMAIL_USE_TLS = True

DEFAULT_FROM_EMAIL = os.getenv(
    "BREVO_FROM_EMAIL",
    "noreply@example.com",
)
```

If the project uses Django 6.x, also verify the current Django mailer/settings API before changing an existing project configuration. The classic EMAIL_HOST/EMAIL_PORT/EMAIL_HOST_USER/EMAIL_HOST_PASSWORD/EMAIL_USE_TLS settings remain documented, but Django 6.1 marks several classic settings as deprecated in favor of the `MAILERS` configuration. Do not perform a broad settings migration unless the project actually requires it.

---

# 3. Environment loading

Make sure the existing project already loads `.env`.

If not, use the project's existing environment-variable package/configuration. Do not introduce duplicate environment-loading mechanisms unnecessarily.

Example `.env`:

```env
BREVO_SMTP_HOST=smtp-relay.brevo.com
BREVO_SMTP_PORT=587
BREVO_SMTP_USER=...
BREVO_SMTP_PASSWORD=...
BREVO_FROM_EMAIL=...
BREVO_FROM_NAME=AnyBooking
```

Never expose `BREVO_SMTP_PASSWORD` to React/Next.js/browser code.

---

# 4. First test SMTP before implementing verification

Run:

```bash
python manage.py shell
```

Then:

```python
from django.core.mail import send_mail

send_mail(
    subject="AnyBooking SMTP Test",
    message="Brevo SMTP is working.",
    from_email=None,
    recipient_list=["YOUR_TEST_EMAIL@example.com"],
    fail_silently=False,
)
```

Expected result:
- Django connects to Brevo.
- Brevo accepts the message.
- Test recipient receives the email.

If it fails, fix SMTP before implementing account verification.

Useful checks:
- SMTP login is correct.
- SMTP key is correct.
- Sender is verified in Brevo.
- Port 587 is reachable.
- TLS is enabled.
- `.env` is actually loaded.
- Do not confuse SMTP key with API key.

---

# 5. Database design

Do not store a raw verification token in the database if avoidable.

Recommended model:

```python
class EmailVerificationToken(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="email_verification_tokens",
    )
    token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["expires_at"]),
        ]
```

The user/account model should have an explicit verification state, for example:

```python
email_verified = models.BooleanField(default=False)
```

If the existing user model already has a suitable verification field, reuse it instead of creating a duplicate.

Do not store the user's password until the password-creation step.

---

# 6. Verification token generation

Use Python's `secrets` module.

Example:

```python
import hashlib
import secrets

raw_token = secrets.token_urlsafe(32)

token_hash = hashlib.sha256(
    raw_token.encode("utf-8")
).hexdigest()
```

Store only `token_hash`.

Put the `raw_token` in the verification URL.

Example:

```text
http://localhost:8000/api/auth/verify-email/?token=<raw_token>
```

For production:

```text
https://yourdomain.com/api/auth/verify-email/?token=<raw_token>
```

Never log the raw token.

---

# 7. Token expiration

Use a short lifetime, for example:

```python
from datetime import timedelta
from django.utils import timezone

expires_at = timezone.now() + timedelta(minutes=30)
```

The exact lifetime can be changed later.

Verification must fail when:

```python
token.expires_at <= timezone.now()
```

It must also fail if:

```python
token.used_at is not None
```

---

# 8. Signup flow

Recommended behavior:

### POST /api/auth/signup/

Input:

```json
{
  "email": "user@example.com"
}
```

Server:

1. Normalize the email.
2. Validate it.
3. Check whether an account already exists.
4. If a verified account exists, return an appropriate response.
5. If an unverified account exists, decide whether to resend/reuse verification rather than creating duplicate accounts.
6. Create an unverified user if needed.
7. Generate a secure raw token.
8. Store only its SHA-256 hash.
9. Set expiration.
10. Send verification email.
11. Return a generic success response.

Do not reveal unnecessary information such as whether a sensitive account exists.

Example response:

```json
{
  "message": "If this email can be registered, a verification email has been sent."
}
```

---

# 9. Verification email

Create a reusable Django email template.

Suggested files:

```text
templates/
  emails/
    verify_email.html
    verify_email.txt
```

HTML email should contain:
- AnyBooking branding/name
- Short explanation
- Verify Email button
- Expiration information
- Plain-text fallback

Example link:

```python
verification_url = (
    f"{FRONTEND_BASE_URL}/verify-email?token={raw_token}"
)
```

IMPORTANT:
Use a frontend verification page if the application is a SPA/Next.js frontend.

Recommended flow:

```text
Email
  ↓
https://frontend-domain.com/verify-email?token=...
  ↓
Frontend calls Django verification API
  ↓
Django validates token
```

Do not put SMTP credentials or database logic in frontend code.

---

# 10. Sending the HTML email

Use Django's email API.

Example:

```python
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

context = {
    "verification_url": verification_url,
    "expires_minutes": 30,
}

text_content = render_to_string(
    "emails/verify_email.txt",
    context,
)

html_content = render_to_string(
    "emails/verify_email.html",
    context,
)

email = EmailMultiAlternatives(
    subject="Verify your AnyBooking email",
    body=text_content,
    from_email=None,
    to=[user.email],
)

email.attach_alternative(html_content, "text/html")
email.send(fail_silently=False)
```

Django officially supports `EmailMultiAlternatives` for multipart text/HTML messages.

---

# 11. Verification API

Example:

### POST /api/auth/verify-email/

Input:

```json
{
  "token": "<raw-token>"
}
```

Server:

1. Hash the supplied token.
2. Find the matching token.
3. Reject if not found.
4. Reject if expired.
5. Reject if already used.
6. Mark user `email_verified=True`.
7. Mark token `used_at=timezone.now()`.
8. Return success.

Example:

```python
token_hash = hashlib.sha256(
    raw_token.encode("utf-8")
).hexdigest()

verification = EmailVerificationToken.objects.select_related(
    "user"
).filter(
    token_hash=token_hash
).first()
```

Use a database transaction when updating both the token and user.

---

# 12. Create-password flow

After verification, the frontend shows:

```text
Email verified ✓

Create password
Confirm password

[Create Password]
```

Recommended API:

### POST /api/auth/create-password/

Input:

```json
{
  "token": "<temporary authenticated credential or secure setup token>",
  "password": "..."
}
```

Do not reuse an already-consumed email verification token as a long-lived password-creation credential.

Preferred implementation:
- After successful email verification, issue a short-lived, purpose-specific password-setup token/session.
- Allow password creation only with that credential.
- Expire it quickly.
- Mark it used after successful password creation.

Alternative if the project already has session/JWT infrastructure:
- Verify email.
- Create a short-lived authenticated session.
- Require that session for password creation.
- Then require normal login afterward.

The agent implementing this must inspect the project's existing authentication system before choosing between these options.

---

# 13. Password storage

Never store plaintext passwords.

Use Django's password hashing system:

```python
from django.contrib.auth import get_user_model

user.set_password(raw_password)
user.save()
```

Do not manually implement bcrypt/PBKDF2/Argon2 hashing if Django's authentication system is already being used.

After password creation:
- mark account/password setup complete
- invalidate any setup token
- allow normal login

---

# 14. Login rules

Normal login should require:

```text
email + password
```

and the account should be considered active only when:

```text
email_verified == True
AND
password has been created
```

Do not allow an unverified account to bypass email verification simply by calling the login API.

---

# 15. Resend verification

Create:

### POST /api/auth/resend-verification/

Input:

```json
{
  "email": "user@example.com"
}
```

Behavior:
- Rate-limit requests.
- Do not generate unlimited tokens.
- Invalidate previous active verification tokens or ensure only the newest token is accepted.
- Generate a new secure token.
- Send a new email.
- Return a generic response.

Suggested limits:
- Per email: e.g. 3 requests/hour
- Per IP: e.g. 10 requests/hour

Exact limits should be adjusted to the application's expected traffic.

---

# 16. Security requirements

The implementation MUST include:

- HTTPS in production.
- SMTP secret only on backend.
- Secure random verification tokens.
- Store token hashes, not raw tokens.
- Token expiration.
- One-time token usage.
- Rate limiting for signup/resend/verification endpoints.
- Generic responses where account enumeration could occur.
- Password hashing through Django.
- CSRF/authentication protections appropriate to the existing frontend/backend architecture.
- Do not log verification tokens or passwords.
- Do not put SMTP credentials in frontend environment variables.
- Do not commit `.env`.

---

# 17. Local development URLs

During local development, configure:

```env
FRONTEND_BASE_URL=http://localhost:3000
BACKEND_BASE_URL=http://localhost:8000
```

If the frontend is Django templates instead of Next.js, use the backend URL instead.

The email can contain:

```text
http://localhost:3000/verify-email?token=...
```

The frontend then calls:

```text
POST http://localhost:8000/api/auth/verify-email/
```

When deployed, change the environment variables:

```env
FRONTEND_BASE_URL=https://your-real-domain.com
BACKEND_BASE_URL=https://api.your-real-domain.com
```

Do not hard-code production URLs.

---

# 18. Production Brevo setup

Before production:
1. Authenticate the sending domain in Brevo.
2. Configure the DNS records Brevo provides.
3. Verify the transactional sender.
4. Keep SMTP credentials in server environment variables/secrets.
5. Monitor Brevo transactional logs.
6. Test Gmail, Outlook, etc.
7. Check spam/deliverability.
8. Configure production frontend/backend URLs.

Brevo recommends domain authentication for deliverability and requires/configures verified senders for transactional mail.

---

# 19. Suggested Django project structure

Adapt this to the existing project rather than blindly creating duplicate apps:

```text
backend/
├── manage.py
├── config/
│   ├── settings.py
│   ├── urls.py
│   └── ...
├── accounts/
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   ├── services/
│   │   └── email_verification.py
│   └── ...
├── templates/
│   └── emails/
│       ├── verify_email.html
│       └── verify_email.txt
└── .env
```

Recommended separation:

```text
views.py
  ↓
authentication service
  ↓
email verification service
  ↓
Django email backend
  ↓
Brevo SMTP
```

Keep email construction/sending out of large view functions.

---

# 20. Email service function

Create a reusable function similar to:

```python
def send_verification_email(user, raw_token):
    ...
```

The function should:
- build the verification URL
- render HTML and text templates
- send the email
- raise/log an appropriate error if delivery submission fails

Do not silently swallow errors during development.

---

# 21. Testing checklist

### SMTP
- [ ] SMTP credentials load correctly
- [ ] Test email reaches inbox
- [ ] Wrong credentials fail clearly
- [ ] HTML email renders correctly

### Signup
- [ ] Valid email creates unverified account
- [ ] Verification email is sent
- [ ] Duplicate signup is handled
- [ ] No password is created at signup

### Verification
- [ ] Valid token verifies account
- [ ] Invalid token rejected
- [ ] Expired token rejected
- [ ] Used token rejected
- [ ] Token cannot be reused
- [ ] User is marked verified

### Password
- [ ] Password cannot be created before verification
- [ ] Password is hashed
- [ ] Weak/invalid password is rejected according to project policy
- [ ] Setup credential expires
- [ ] Setup credential cannot be reused

### Login
- [ ] Verified user can log in
- [ ] Unverified user cannot bypass verification
- [ ] Wrong password rejected

### Resend
- [ ] Resend works
- [ ] Old token is invalidated/controlled
- [ ] Rate limiting works

### Production
- [ ] HTTPS
- [ ] Domain authenticated in Brevo
- [ ] Sender verified
- [ ] Secrets stored outside source code
- [ ] Production URLs configured
- [ ] Transactional logs checked

---

# 22. Agent implementation rules

If an AI coding agent is implementing this document:

1. FIRST inspect the existing Django project.
2. Identify the existing User model/authentication system.
3. Identify whether Django REST Framework is used.
4. Identify existing API URL conventions.
5. Identify how environment variables are currently loaded.
6. Identify the frontend URL and authentication flow.
7. Reuse existing user/account models where possible.
8. Do not create a second authentication system unnecessarily.
9. Do not replace existing authentication libraries without a reason.
10. Do not overwrite unrelated code.
11. Run migrations after model changes.
12. Run Django checks.
13. Run tests.
14. Test actual Brevo SMTP delivery.
15. Report every changed file and command executed.
16. Never expose the SMTP key in source code, logs, API responses, or frontend bundles.

---

# 23. Minimal implementation sequence

Implement in this order:

### Phase 1 — SMTP
- Add `.env` variables.
- Configure Django email backend.
- Send a test email.

### Phase 2 — Verification model
- Add `email_verified`.
- Add `EmailVerificationToken`.
- Create migration.
- Migrate.

### Phase 3 — Signup
- Accept email.
- Create unverified account.
- Generate token.
- Send verification email.

### Phase 4 — Verification
- Add verify endpoint.
- Validate token.
- Mark email verified.
- Consume token.

### Phase 5 — Password creation
- Add short-lived setup credential/session.
- Add create-password endpoint.
- Hash password using Django.
- Invalidate setup credential.

### Phase 6 — Login
- Require verified account.
- Authenticate with email/password.
- Return the project's existing authentication/session/JWT response.

### Phase 7 — Resend
- Add resend endpoint.
- Add rate limiting.
- Invalidate/expire old tokens.

### Phase 8 — Production hardening
- Domain authentication.
- HTTPS.
- Secrets.
- Rate limits.
- Logs.
- Tests.
- Production email testing.

---

# 24. Final target behavior

The completed system should behave exactly like:

```text
SIGN UP
  ↓
Email only
  ↓
Unverified account
  ↓
Brevo sends verification email
  ↓
User clicks link
  ↓
Django validates secure one-time token
  ↓
Email verified
  ↓
Create password
  ↓
Django hashes password
  ↓
Account ready
  ↓
Login with email + password
```

The important boundary is:

```text
Django = authentication + verification + database + security
Brevo  = transactional email delivery
```

Do not make the frontend decide whether an email is verified. The backend/database must be the source of truth.

## Official documentation to use while implementing

- Brevo SMTP setup: https://help.brevo.com/hc/en-us/articles/7924908994450-Send-transactional-emails-using-Brevo-SMTP
- Brevo SMTP keys: https://help.brevo.com/hc/en-us/articles/7959631848850-Create-and-manage-your-SMTP-keys
- Brevo SMTP ports: https://help.brevo.com/hc/en-us/articles/10905415650322-Which-SMTP-port-should-I-use-Port-587-465-or-2525
- Django email documentation: https://docs.djangoproject.com/en/6.0/topics/email/
