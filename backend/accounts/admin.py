from django.contrib import admin
from .models import UserProfile, EmailVerificationToken, PasswordSetupToken


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'email_verified', 'password_set', 'created_at')
    list_filter = ('role', 'email_verified', 'password_set')
    search_fields = ('user__email', 'user__username')
    readonly_fields = ('created_at',)


@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'expires_at', 'used_at', 'created_at')
    list_filter = ('used_at',)
    search_fields = ('user__email',)
    readonly_fields = ('code_hash', 'created_at')


@admin.register(PasswordSetupToken)
class PasswordSetupTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'expires_at', 'used_at', 'created_at')
    list_filter = ('used_at',)
    search_fields = ('user__email',)
    readonly_fields = ('token_hash', 'created_at')
