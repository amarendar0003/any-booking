"""
Accounts views — signup, email OTP verification, password creation, login/logout.
All endpoints return JSON so they work seamlessly from the auth modal via fetch().
"""
import logging
import re

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from .models import UserProfile, EmailVerificationToken, PasswordSetupToken
from .services.email import send_otp_email

logger = logging.getLogger(__name__)


# ── helpers ──────────────────────────────────────────────────────────────────

def _json_ok(data: dict) -> JsonResponse:
    return JsonResponse({'ok': True, **data})


def _json_err(message: str, status: int = 400) -> JsonResponse:
    return JsonResponse({'ok': False, 'error': message}, status=status)


# ── Signup Step 1: submit email + role ───────────────────────────────────────

@require_POST
@csrf_protect
def signup_view(request):
    """
    POST /accounts/signup/
    Body: { name, phone, email, role }
    Creates an unverified user (or reuses an existing unverified one),
    generates a 5-minute OTP and emails it via Brevo.
    Name is stored on the User (first_name); phone on UserProfile.
    """
    email = request.POST.get('email', '').strip().lower()
    role = request.POST.get('role', '').strip()
    name = request.POST.get('name', '').strip()
    phone = request.POST.get('phone', '').strip()

    if not email:
        return _json_err('Email is required.')
    if not name:
        return _json_err('Name is required.')
    if not phone:
        return _json_err('Phone number is required.')
    if not re.fullmatch(r'[0-9+\-\s()]{7,20}', phone):
        return _json_err('Please enter a valid phone number.')
    if role not in (UserProfile.ROLE_CUSTOMER, UserProfile.ROLE_VENDOR):
        return _json_err('Please select a valid role (customer or vendor).')

    # Generic response regardless of whether account exists —
    # avoids account enumeration.
    try:
        existing_user = User.objects.filter(email=email).first()

        if existing_user:
            profile = getattr(existing_user, 'profile', None)
            if profile and profile.email_verified and profile.password_set:
                # Fully registered — don't allow re-registration
                return _json_ok({
                    'message': (
                        'If this email can be registered, a verification '
                        'code has been sent.'
                    )
                })
            # Unverified or incomplete — allow resend and refresh details
            user = existing_user
            user.first_name = name[:150]
            user.save(update_fields=['first_name'])
            if profile:
                profile.role = role
                profile.phone = phone
                profile.save(update_fields=['role', 'phone'])
        else:
            # Create a new inactive user (no usable password yet)
            with transaction.atomic():
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    password=None,  # No password until create-password step
                    first_name=name[:150],
                )
                user.is_active = False  # Will activate after verification
                user.save(update_fields=['is_active'])
                UserProfile.objects.create(user=user, role=role, phone=phone)

        # Generate OTP and send email
        _, raw_otp = EmailVerificationToken.generate_for_user(user)
        send_otp_email(user, raw_otp)

    except Exception as exc:
        logger.exception('Error during signup for %s', email)
        return _json_err('Something went wrong. Please try again.')

    return _json_ok({
        'message': (
            'If this email can be registered, a verification '
            'code has been sent.'
        )
    })


# ── Signup Step 2: verify OTP ────────────────────────────────────────────────

@require_POST
@csrf_protect
def verify_email_view(request):
    """
    POST /accounts/verify-email/
    Body: { email, otp }
    Validates OTP, marks email verified, returns a short-lived setup_token
    for the password-creation step.
    """
    email = request.POST.get('email', '').strip().lower()
    otp = request.POST.get('otp', '').strip()

    if not email or not otp:
        return _json_err('Email and OTP are required.')

    user = User.objects.filter(email=email).first()
    if not user:
        return _json_err('Invalid verification code.', status=400)

    token = EmailVerificationToken.validate_otp(user, otp)
    if token is None:
        return _json_err('Invalid or expired verification code.')

    with transaction.atomic():
        token.used_at = timezone.now()
        token.save(update_fields=['used_at'])

        profile = user.profile
        profile.email_verified = True
        profile.save(update_fields=['email_verified'])

        # Activate the user account
        user.is_active = True
        user.save(update_fields=['is_active'])

        # Issue a short-lived password-setup token
        _, raw_setup_token = PasswordSetupToken.generate_for_user(user)

    return _json_ok({
        'message': 'Email verified successfully.',
        'setup_token': raw_setup_token,
    })


# ── Signup Step 3: create password ───────────────────────────────────────────

@require_POST
@csrf_protect
def create_password_view(request):
    """
    POST /accounts/create-password/
    Body: { setup_token, password, password2 }
    Sets the user's password and logs them in.
    """
    raw_token = request.POST.get('setup_token', '').strip()
    password = request.POST.get('password', '')
    password2 = request.POST.get('password2', '')

    if not raw_token:
        return _json_err('Setup token is required.')
    if not password:
        return _json_err('Password is required.')
    if password != password2:
        return _json_err('Passwords do not match.')

    setup_token = PasswordSetupToken.validate_token(raw_token)
    if setup_token is None:
        return _json_err('Setup session expired. Please start signup again.')

    user = setup_token.user

    # Validate password strength
    try:
        validate_password(password, user=user)
    except ValidationError as exc:
        return _json_err(' '.join(exc.messages))

    with transaction.atomic():
        # Mark setup token as used
        setup_token.used_at = timezone.now()
        setup_token.save(update_fields=['used_at'])

        # Set hashed password
        user.set_password(password)
        user.save(update_fields=['password'])

        profile = user.profile
        profile.password_set = True
        profile.save(update_fields=['password_set'])

        # Auto-create Vendor profile if role is vendor
        if profile.role == UserProfile.ROLE_VENDOR:
            _ensure_vendor_profile(user)

    # Log the user in
    login(request, user, backend='django.contrib.auth.backends.ModelBackend')

    redirect_url = _post_login_redirect(user)
    return _json_ok({
        'message': 'Account created successfully.',
        'redirect': redirect_url,
    })


# ── Login ─────────────────────────────────────────────────────────────────────

@require_POST
@csrf_protect
def login_view(request):
    """
    POST /accounts/login/
    Body: { email, password }
    """
    email = request.POST.get('email', '').strip().lower()
    password = request.POST.get('password', '')

    if not email or not password:
        return _json_err('Email and password are required.')

    # Django authenticate uses the username field; signup sets username = email,
    # so email + password is the single login path for every role.
    user = authenticate(request, username=email, password=password)
    if user is None:
        return _json_err('Invalid email or password.', status=401)

    # Superusers sign in via Django /admin/ only — never through this modal.
    if user.is_superuser:
        return _json_err('Please sign in from the admin console.', status=403)

    profile = getattr(user, 'profile', None)

    if profile is None:
        # Account without a UserProfile (e.g. vendor staff created via the
        # Django admin) — allow through; _post_login_redirect routes them.
        login(request, user)
        return _json_ok({'redirect': _post_login_redirect(user)})

    if not profile.email_verified:
        return _json_err(
            'Please verify your email first. '
            'Check your inbox for the verification code.',
            status=403,
        )

    if not profile.password_set:
        return _json_err(
            'Account setup is incomplete. Please complete signup.',
            status=403,
        )

    login(request, user)
    redirect_url = _post_login_redirect(user)
    return _json_ok({'redirect': redirect_url})


# ── Logout ───────────────────────────────────────────────────────────────────

@require_POST
@csrf_protect
def logout_view(request):
    """POST /accounts/logout/"""
    logout(request)
    return _json_ok({'redirect': '/'})


# ── Resend OTP ────────────────────────────────────────────────────────────────

@require_POST
@csrf_protect
def resend_otp_view(request):
    """
    POST /accounts/resend-otp/
    Body: { email }
    Resends a fresh OTP. Existing tokens are invalidated.
    """
    email = request.POST.get('email', '').strip().lower()
    if not email:
        return _json_err('Email is required.')

    user = User.objects.filter(email=email).first()
    if user:
        profile = getattr(user, 'profile', None)
        if profile and not profile.email_verified:
            try:
                _, raw_otp = EmailVerificationToken.generate_for_user(user)
                send_otp_email(user, raw_otp)
            except Exception:
                logger.exception('Failed to resend OTP to %s', email)

    # Always return generic message
    return _json_ok({
        'message': 'If this email is registered and unverified, a new code has been sent.'
    })


# ── private helpers ───────────────────────────────────────────────────────────

def _post_login_redirect(user) -> str:
    """Return the appropriate post-login URL based on user role."""
    profile = getattr(user, 'profile', None)
    if profile and profile.role == UserProfile.ROLE_VENDOR:
        return '/vendor/dashboard/'
    # Vendor owner/staff accounts created via the Django admin have no
    # UserProfile — send them to the vendor portal as well.
    try:
        from vendors.views import _resolve_vendor_role
        if _resolve_vendor_role(user)[0] is not None:
            return '/vendor/dashboard/'
    except Exception:
        pass
    if user.is_staff or user.is_superuser:
        return '/admin/'
    return '/'


def _ensure_vendor_profile(user):
    """
    Auto-create a Vendor profile for users who signed up as vendor.
    Vendor.user is a OneToOneField on services.Vendor — auto-approved.
    Uses the name and phone captured at signup.
    """
    try:
        from services.models import Vendor
        if not hasattr(user, 'vendor_profile'):
            profile = getattr(user, 'profile', None)
            phone = (getattr(profile, 'phone', '') or '')[:20]
            Vendor.objects.create(
                user=user,
                name=user.get_full_name() or user.email.split('@')[0],
                email=user.email,
                phone=phone,
                is_active=True,
            )
    except Exception:
        logger.exception('Could not auto-create vendor profile for %s', user.email)


def _get_vendor_model():
    try:
        from services.models import Vendor
        return Vendor
    except ImportError:
        return None
