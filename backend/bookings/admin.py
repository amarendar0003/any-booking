from django.contrib import admin, messages
from django.shortcuts import render
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline
from services.admin_mixins import LocationRestrictedMixin
from .audit import log_booking_status_change
from .models import Booking, BlockedDate, EmailLog


# ── Bulk actions ──────────────────────────────────────────────────────────────

@admin.action(description='✅ Approve & notify customer')
def approve_bookings(modeladmin, request, queryset):
    from .emails import send_booking_approved
    eligible = queryset.filter(status=Booking.STATUS_PENDING)
    count = 0
    for booking in eligible:
        booking.status = Booking.STATUS_CONFIRMED
        booking.save(update_fields=['status', 'updated_at'])
        log_booking_status_change(request.user, booking, 'Approved via admin bulk action (pending → confirmed)')
        send_booking_approved(booking, sent_by=request.user)
        count += 1
    if count:
        modeladmin.message_user(request, f'{count} booking(s) approved and confirmation emails sent.', messages.SUCCESS)
    skipped = queryset.count() - count
    if skipped:
        modeladmin.message_user(request, f'{skipped} booking(s) skipped (not in Pending status).', messages.WARNING)


@admin.action(description='❌ Cancel with refund & notify customer')
def cancel_with_refund(modeladmin, request, queryset):
    """Two-step action: shows an intermediate form to collect refund info."""
    from .emails import send_booking_cancelled

    eligible = queryset.exclude(status=Booking.STATUS_COMPLETED)

    # Step 2: form submitted
    if request.POST.get('confirmed'):
        refund_type = request.POST.get('refund_type', Booking.REFUND_NONE)
        refund_amount_raw = request.POST.get('refund_amount', '').strip()
        cancellation_reason = request.POST.get('cancellation_reason', '').strip()
        admin_notes = request.POST.get('admin_notes', '').strip()

        refund_amount = None
        if refund_type == Booking.REFUND_PARTIAL and refund_amount_raw:
            try:
                refund_amount = float(refund_amount_raw)
            except ValueError:
                pass

        count = 0
        for booking in eligible:
            booking.status = Booking.STATUS_CANCELLED
            booking.refund_type = refund_type
            booking.refund_amount = refund_amount
            booking.cancellation_reason = cancellation_reason
            if admin_notes:
                booking.admin_notes = admin_notes
            booking.save(update_fields=[
                'status', 'refund_type', 'refund_amount',
                'cancellation_reason', 'admin_notes', 'updated_at'
            ])
            log_booking_status_change(
                request.user, booking,
                f'Cancelled via admin bulk action (refund: {refund_type})',
            )
            send_booking_cancelled(booking, sent_by=request.user)
            count += 1

        modeladmin.message_user(
            request,
            f'{count} booking(s) cancelled and notification emails sent.',
            messages.SUCCESS,
        )
        skipped = queryset.count() - count
        if skipped:
            modeladmin.message_user(request, f'{skipped} booking(s) skipped (already Completed).', messages.WARNING)
        return None

    # Step 1: render intermediate form
    return render(request, 'admin/bookings/cancel_refund_form.html', {
        'bookings': eligible,
        'title': 'Cancel Bookings with Refund',
    })


@admin.action(description='🏁 Mark selected bookings as Completed')
def complete_bookings(modeladmin, request, queryset):
    count = 0
    for booking in queryset.filter(status=Booking.STATUS_CONFIRMED):
        booking.status = Booking.STATUS_COMPLETED
        booking.save(update_fields=['status', 'updated_at'])
        log_booking_status_change(request.user, booking, 'Marked completed via admin bulk action (confirmed → completed)')
        count += 1
    modeladmin.message_user(request, f'{count} booking(s) marked as Completed.', messages.SUCCESS)


# ── Booking admin ─────────────────────────────────────────────────────────────

class TermsAcceptanceInline(TabularInline):
    from terms.models import TermsAcceptance
    model = TermsAcceptance
    extra = 0
    can_delete = False
    fields = ('terms', 'version_at_acceptance', 'ip_address', 'accepted_at')
    readonly_fields = ('terms', 'version_at_acceptance', 'ip_address', 'accepted_at')
    verbose_name_plural = 'Terms Acceptances'

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Booking)
class BookingAdmin(LocationRestrictedMixin, ModelAdmin):
    city_path = 'service__city'
    list_display = (
        'confirmation_number', 'customer_name', 'service_link',
        'event_date', 'total_amount', 'status_badge',
        'cancel_request_badge', 'created_at'
    )
    list_filter = ('status', 'cancellation_requested', 'event_date', 'service__category',
                   'service__city__district__state__country', 'service__city__district__state')
    search_fields = ('confirmation_number', 'customer_name', 'customer_email', 'customer_phone', 'service__name')
    readonly_fields = ('confirmation_number', 'created_at', 'updated_at', 'balance_amount_display',
                       'email_log_summary',
                       'cancellation_requested', 'cancellation_requested_at', 'cancellation_request_reason')
    list_editable = ()
    date_hierarchy = 'event_date'
    actions = [approve_bookings, cancel_with_refund, complete_bookings]
    inlines = [TermsAcceptanceInline]
    fieldsets = (
        ('Customer Details', {
            'fields': ('confirmation_number', 'customer_name', 'customer_email', 'customer_phone')
        }),
        ('Booking Details', {
            'fields': ('service', 'event_date', 'event_end_date', 'event_time', 'guest_count', 'special_requests')
        }),
        ('Financial', {
            'fields': ('total_amount', 'advance_amount', 'balance_amount_display')
        }),
        ('Status & Notes', {
            'fields': ('status', 'admin_notes', 'created_at', 'updated_at')
        }),
        ('Customer Cancellation Request', {
            'fields': ('cancellation_requested', 'cancellation_requested_at', 'cancellation_request_reason'),
            'classes': ('collapse',),
        }),
        ('Cancellation / Refund', {
            'fields': ('cancellation_reason', 'refund_type', 'refund_amount'),
            'classes': ('collapse',),
        }),
        ('Email Communications', {
            'fields': ('email_log_summary',),
            'classes': ('collapse',),
        }),
    )
    # Terms acceptances shown via TermsAcceptanceInline below the fieldsets

    def service_link(self, obj):
        name = obj.service.name
        label = name[:30] + '…' if len(name) > 30 else name
        return format_html(
            '<a href="/admin/services/service/{}/change/" title="{}">{}</a>',
            obj.service_id, name, label
        )
    service_link.short_description = 'Service'

    def status_badge(self, obj):
        colors = {
            'pending': '#d97706',
            'confirmed': '#16a34a',
            'cancelled': '#dc2626',
            'completed': '#2563eb',
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background:{};color:white;padding:3px 10px;'
            'border-radius:999px;font-size:12px;font-weight:700">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def cancel_request_badge(self, obj):
        if not obj.cancellation_requested:
            return ''
        return format_html(
            '<span style="background:#fef3c7;color:#92400e;padding:2px 8px;'
            'border-radius:4px;font-size:11px;font-weight:600">⚠ Requested</span>'
        )
    cancel_request_badge.short_description = 'Cancel Req.'

    def balance_amount_display(self, obj):
        if obj.total_amount is None:
            return '—'
        return f'₹{obj.balance_amount:,.2f}'
    balance_amount_display.short_description = 'Balance'

    def email_log_summary(self, obj):
        if obj.pk is None:
            return 'No emails sent yet.'
        logs = obj.email_logs.order_by('-sent_at')[:10]
        if not logs:
            return 'No emails sent yet.'
        rows = ''.join(
            f'<tr>'
            f'<td style="padding:4px 8px;font-size:12px">{l.sent_at.strftime("%d %b %Y %H:%M")}</td>'
            f'<td style="padding:4px 8px;font-size:12px">{l.get_email_type_display()}</td>'
            f'<td style="padding:4px 8px;font-size:12px">{l.recipient_email}</td>'
            f'<td style="padding:4px 8px;font-size:12px">'
            f'<span style="color:{"#16a34a" if l.status == "sent" else "#dc2626"};font-weight:600">'
            f'{l.status.upper()}</span></td>'
            f'</tr>'
            for l in logs
        )
        return format_html(
            '<table style="border-collapse:collapse;width:100%">'
            '<thead><tr style="background:#f3f4f6">'
            '<th style="padding:4px 8px;text-align:left;font-size:12px">Time</th>'
            '<th style="padding:4px 8px;text-align:left;font-size:12px">Type</th>'
            '<th style="padding:4px 8px;text-align:left;font-size:12px">Recipient</th>'
            '<th style="padding:4px 8px;text-align:left;font-size:12px">Status</th>'
            '</tr></thead><tbody>{}</tbody></table>',
            format_html(rows)
        )
    email_log_summary.short_description = 'Email History'


# ── BlockedDate admin ─────────────────────────────────────────────────────────

@admin.action(description='🗑 Remove selected blocked dates')
def clear_blocked_dates(modeladmin, request, queryset):
    count = queryset.count()
    queryset.delete()
    modeladmin.message_user(request, f'{count} blocked date(s) removed.', messages.SUCCESS)


@admin.register(BlockedDate)
class BlockedDateAdmin(LocationRestrictedMixin, ModelAdmin):
    city_path = 'service__city'
    list_display = (
        'date', 'service_link', 'category_badge', 'city_name', 'state_name', 'country_name', 'reason'
    )
    list_filter = (
        'service__category',
        'service__city__district__state__country',
        'service__city__district__state',
        'service__city',
        'date',
    )
    search_fields = ('service__name', 'service__city__name', 'reason')
    date_hierarchy = 'date'
    list_select_related = ('service__category', 'service__city__district__state__country')
    actions = [clear_blocked_dates]
    autocomplete_fields = ['service']
    fieldsets = (
        (None, {
            'fields': ('service', 'date', 'reason'),
            'description': 'Block a specific date for this service — it will appear unavailable to customers.'
        }),
    )

    def service_link(self, obj):
        return format_html(
            '<a href="/admin/services/service/{}/change/">{}</a>',
            obj.service_id, obj.service.name
        )
    service_link.short_description = 'Service'
    service_link.admin_order_field = 'service__name'

    def category_badge(self, obj):
        cat = obj.service.category
        return format_html(
            '<span style="background:#e8f0fe;color:#1a56db;padding:2px 8px;border-radius:4px;font-size:12px">{}</span>',
            cat.get_slug_display()
        )
    category_badge.short_description = 'Category'
    category_badge.admin_order_field = 'service__category__slug'

    def city_name(self, obj):
        return obj.service.city.name if obj.service.city else '—'
    city_name.short_description = 'City'
    city_name.admin_order_field = 'service__city__name'

    def state_name(self, obj):
        return obj.service.city.state.name if obj.service.city else '—'
    state_name.short_description = 'State'
    state_name.admin_order_field = 'service__city__district__state__name'

    def country_name(self, obj):
        return obj.service.city.country.name if obj.service.city else '—'
    country_name.short_description = 'Country'
    country_name.admin_order_field = 'service__city__district__state__country__name'


# ── EmailLog admin ────────────────────────────────────────────────────────────

@admin.register(EmailLog)
class EmailLogAdmin(ModelAdmin):
    list_display = (
        'sent_at', 'email_type_badge', 'recipient_email',
        'subject_short', 'status_badge', 'sent_by'
    )
    list_filter = ('email_type', 'status', 'sent_at')
    search_fields = ('recipient_email', 'subject', 'booking__customer_name')
    readonly_fields = (
        'booking', 'email_type', 'recipient_email', 'recipient_name',
        'subject', 'body_preview', 'status', 'error_message', 'sent_by', 'sent_at'
    )
    date_hierarchy = 'sent_at'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # Area admins see only logs for bookings in their region
        try:
            profile = request.user.staff_profile
            kwargs = profile.filter_kwargs('booking__service__city')
            return qs.filter(**kwargs) if kwargs else qs
        except Exception:
            return qs.none()

    def email_type_badge(self, obj):
        colors = {
            'booking_received':       ('#dbeafe', '#1e40af'),
            'admin_notify':           ('#fef3c7', '#92400e'),
            'booking_approved':       ('#d1fae5', '#065f46'),
            'booking_cancelled':      ('#fee2e2', '#991b1b'),
            'cancel_request_customer':('#fef9c3', '#713f12'),
            'cancel_request_admin':   ('#fde68a', '#78350f'),
            'vendor_received':        ('#dbeafe', '#1e40af'),
            'vendor_confirmed':       ('#d1fae5', '#065f46'),
            'vendor_cancelled':       ('#ffe4e6', '#9f1239'),
        }
        bg, fg = colors.get(obj.email_type, ('#f3f4f6', '#374151'))
        return format_html(
            '<span style="background:{};color:{};padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600">{}</span>',
            bg, fg, obj.get_email_type_display()
        )
    email_type_badge.short_description = 'Type'
    email_type_badge.admin_order_field = 'email_type'

    def status_badge(self, obj):
        if obj.status == 'sent':
            return format_html('<span style="color:#16a34a;font-weight:700">✓ Sent</span>')
        return format_html('<span style="color:#dc2626;font-weight:700">✗ Failed</span>')
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'

    def booking_link(self, obj):
        return format_html(
            '<a href="/admin/bookings/booking/{}/change/">#{}</a>',
            obj.booking_id, obj.booking_id
        )
    booking_link.short_description = 'Booking'
    booking_link.admin_order_field = 'booking_id'

    def subject_short(self, obj):
        return obj.subject[:60] + '…' if len(obj.subject) > 60 else obj.subject
    subject_short.short_description = 'Subject'

    def body_preview(self, obj):
        return format_html(
            '<div style="border:1px solid #e5e7eb;border-radius:6px;padding:12px;'
            'max-height:400px;overflow-y:auto">{}</div>',
            format_html(obj.body_html)
        )
    body_preview.short_description = 'Email Preview'

    fieldsets = (
        ('Message', {
            'fields': ('email_type', 'subject', 'recipient_name', 'recipient_email', 'body_preview')
        }),
        ('Metadata', {
            'fields': ('booking', 'status', 'error_message', 'sent_by', 'sent_at')
        }),
    )
