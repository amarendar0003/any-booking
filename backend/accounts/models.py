import hashlib
import secrets

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class UserProfile(models.Model):
    """
    Extends Django's built-in User with role and email-verification state.
    Created automatically when a user completes signup.
    """
    ROLE_CUSTOMER = 'customer'
    ROLE_VENDOR = 'vendor'
    ROLE_CHOICES = [
        (ROLE_CUSTOMER, 'Customer'),
        (ROLE_VENDOR, 'Vendor'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_CUSTOMER,
    )
    # Contact phone captured during signup — copied into Vendor.phone when
    # the vendor profile is auto-created.
    phone = models.CharField(max_length=20, blank=True)
    email_verified = models.BooleanField(default=False)
    password_set = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        return f'{self.user.email} ({self.role})'


class EmailVerificationToken(models.Model):
    """
    Stores a hashed 6-digit OTP for email verification.
    OTPs expire in 5 minutes and are single-use.
    """
    OTP_LIFETIME_MINUTES = 5

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='email_verification_tokens',
    )
    # SHA-256 hash of the 6-digit numeric OTP — never store raw code
    code_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f'OTP for {self.user.email} (expires {self.expires_at})'

    @property
    def is_valid(self):
        return self.used_at is None and self.expires_at > timezone.now()

    @classmethod
    def generate_for_user(cls, user):
        """
        Invalidate existing active tokens, generate a new 6-digit OTP,
        store its hash, and return (token_obj, raw_otp).
        """
        # Invalidate all existing unused tokens for this user by expiring them
        cls.objects.filter(user=user, used_at__isnull=True).update(
            expires_at=timezone.now()
        )

        raw_otp = str(secrets.randbelow(900000) + 100000)  # 6-digit: 100000–999999
        code_hash = hashlib.sha256(raw_otp.encode('utf-8')).hexdigest()
        expires_at = timezone.now() + timezone.timedelta(minutes=cls.OTP_LIFETIME_MINUTES)

        token = cls.objects.create(
            user=user,
            code_hash=code_hash,
            expires_at=expires_at,
        )
        return token, raw_otp

    @classmethod
    def validate_otp(cls, user, raw_otp):
        """
        Returns the token object if valid, else None.
        """
        code_hash = hashlib.sha256(raw_otp.encode('utf-8')).hexdigest()
        try:
            token = cls.objects.get(
                user=user,
                code_hash=code_hash,
                used_at__isnull=True,
            )
        except cls.DoesNotExist:
            return None
        if token.expires_at <= timezone.now():
            return None
        return token


class PasswordSetupToken(models.Model):
    """
    Short-lived token issued after successful email verification.
    Used to authorise the password-creation step only.
    Expires in 15 minutes and is single-use.
    """
    LIFETIME_MINUTES = 15

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='password_setup_tokens',
    )
    token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['user'])]

    @classmethod
    def generate_for_user(cls, user):
        """Returns (token_obj, raw_token)."""
        cls.objects.filter(user=user, used_at__isnull=True).update(
            expires_at=timezone.now()
        )
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()
        expires_at = timezone.now() + timezone.timedelta(minutes=cls.LIFETIME_MINUTES)
        token = cls.objects.create(
            user=user,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        return token, raw_token

    @classmethod
    def validate_token(cls, raw_token):
        """Returns token object if valid, else None."""
        token_hash = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()
        try:
            token = cls.objects.get(token_hash=token_hash, used_at__isnull=True)
        except cls.DoesNotExist:
            return None
        if token.expires_at <= timezone.now():
            return None
        return token
