from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from services.admin_mixins import LocationRestrictedMixin
from .models import Payment, PaymentGatewayConfig


@admin.register(Payment)
class PaymentAdmin(LocationRestrictedMixin, ModelAdmin):
    city_path = 'booking__service__city'
    list_display = ('gateway_order_id', 'gateway_badge', 'booking', 'amount', 'currency', 'status_badge', 'created_at')
    list_filter = ('status', 'gateway')
    search_fields = ('gateway_order_id', 'razorpay_payment_id', 'booking__customer_name')
    readonly_fields = ('gateway_order_id', 'gateway', 'razorpay_payment_id', 'razorpay_signature',
                       'currency', 'created_at', 'updated_at')

    def gateway_badge(self, obj):
        colors = {
            'razorpay':  ('#e8f0fe', '#1a56db'),
            'stripe':    ('#f0fdf4', '#166534'),
            'cashfree':  ('#fef3c7', '#92400e'),
            'paystack':  ('#fdf2f8', '#9d174d'),
        }
        bg, fg = colors.get(obj.gateway, ('#f3f4f6', '#374151'))
        return format_html(
            '<span style="background:{};color:{};padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600">{}</span>',
            bg, fg, obj.get_gateway_display()
        )
    gateway_badge.short_description = 'Gateway'

    def status_badge(self, obj):
        colors = {
            'created':  ('#fef3c7', '#92400e'),
            'captured': ('#d1fae5', '#065f46'),
            'failed':   ('#fee2e2', '#991b1b'),
            'refunded': ('#dbeafe', '#1e40af'),
        }
        bg, fg = colors.get(obj.status, ('#f3f4f6', '#374151'))
        return format_html(
            '<span style="background:{};color:{};padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600">{}</span>',
            bg, fg, obj.get_status_display()
        )
    status_badge.short_description = 'Status'


@admin.register(PaymentGatewayConfig)
class PaymentGatewayConfigAdmin(ModelAdmin):
    list_display = ('country', 'gateway_badge', 'is_enabled', 'get_customer_label', 'updated_at')
    list_editable = ('is_enabled',)
    list_filter = ('gateway', 'is_enabled')
    fieldsets = (
        ('Country & Gateway', {
            'fields': ('country', 'gateway', 'is_enabled'),
            'description': (
                'Select the payment gateway for this country and enable it to redirect customers '
                'to online payment after booking. Disable for offline/cash bookings. '
                'API credentials are configured via environment variables — see SETUP.md.'
            ),
        }),
        ('Display', {
            'fields': ('display_name',),
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',),
        }),
    )

    def gateway_badge(self, obj):
        colors = {
            'razorpay':  ('#e8f0fe', '#1a56db'),
            'stripe':    ('#f0fdf4', '#166534'),
            'cashfree':  ('#fef3c7', '#92400e'),
            'paystack':  ('#fdf2f8', '#9d174d'),
        }
        bg, fg = colors.get(obj.gateway, ('#f3f4f6', '#374151'))
        return format_html(
            '<span style="background:{};color:{};padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600">{}</span>',
            bg, fg, obj.get_gateway_display()
        )
    gateway_badge.short_description = 'Gateway'

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_module_perms(self, request):
        return request.user.is_superuser
