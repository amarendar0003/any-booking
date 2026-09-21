from django.contrib import admin
from django.utils.html import format_html, mark_safe
from unfold.admin import ModelAdmin, TabularInline
from .models import TermsOfUse, TermsAcceptance


class TermsAcceptanceInline(TabularInline):
    model = TermsAcceptance
    extra = 0
    can_delete = False
    fields = ('terms', 'version_at_acceptance', 'ip_address', 'accepted_at')
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(TermsOfUse)
class TermsOfUseAdmin(ModelAdmin):
    list_display = ('title', 'version', 'scope_badge', 'service', 'is_active', 'acceptance_count', 'updated_at')
    list_display_links = ('title',)
    list_editable = ('is_active',)
    list_filter = ('is_active', 'scope')
    search_fields = ('title', 'content', 'service__name')
    autocomplete_fields = ('service',)
    readonly_fields = ('created_at', 'updated_at', 'content_preview')
    fieldsets = (
        ('Identity', {
            'fields': ('title', 'version', 'is_active'),
        }),
        ('Scope', {
            'fields': ('scope', 'service'),
            'description': (
                'Site-wide terms apply to every booking. '
                'Service-specific terms apply only to bookings for the chosen service. '
                'If both are active, the customer must accept both.'
            ),
        }),
        ('Content', {
            'fields': ('content', 'content_preview'),
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    inlines = [TermsAcceptanceInline]

    def scope_badge(self, obj):
        if obj.scope == TermsOfUse.SCOPE_SITE:
            return format_html(
                '<span style="background:#dbeafe;color:#1e40af;padding:2px 8px;'
                'border-radius:4px;font-size:11px;font-weight:600">Site-wide</span>'
            )
        return format_html(
            '<span style="background:#fef3c7;color:#92400e;padding:2px 8px;'
            'border-radius:4px;font-size:11px;font-weight:600">Service</span>'
        )
    scope_badge.short_description = 'Scope'

    def acceptance_count(self, obj):
        n = obj.acceptances.count()
        return format_html('<span style="font-weight:600">{}</span>', n)
    acceptance_count.short_description = 'Accepted'

    def content_preview(self, obj):
        if not obj.pk:
            return '—'
        return format_html(
            '<div style="max-height:300px;overflow-y:auto;border:1px solid #e5e7eb;'
            'border-radius:6px;padding:12px;font-size:13px">{}</div>',
            mark_safe(obj.content),
        )
    content_preview.short_description = 'Rendered Preview'

    def has_delete_permission(self, request, obj=None):
        # Prevent deleting terms that have been accepted (audit trail)
        if obj and obj.acceptances.exists():
            return False
        return super().has_delete_permission(request, obj)


@admin.register(TermsAcceptance)
class TermsAcceptanceAdmin(ModelAdmin):
    list_display = ('booking_link', 'terms_title', 'version_at_acceptance', 'ip_address', 'accepted_at')
    list_filter = ('terms', 'accepted_at')
    search_fields = ('booking__customer_name', 'booking__customer_email', 'terms__title', 'ip_address')
    date_hierarchy = 'accepted_at'
    readonly_fields = ('booking', 'terms', 'version_at_acceptance', 'ip_address', 'user_agent', 'accepted_at')

    def booking_link(self, obj):
        from django.urls import reverse
        url = reverse('admin:bookings_booking_change', args=[obj.booking_id])
        return format_html('<a href="{}">Booking #{} — {}</a>', url, obj.booking_id, obj.booking.customer_name)
    booking_link.short_description = 'Booking'

    def terms_title(self, obj):
        return f'{obj.terms.title} (v{obj.version_at_acceptance})'
    terms_title.short_description = 'Terms'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
