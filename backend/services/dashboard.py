"""
Admin dashboard view — location-aware summary of bookings, revenue, and audit log.
Superusers see all data; staff see only their assigned region.
"""
import json
from datetime import date, timedelta

from django.contrib import admin
from django.contrib.admin.models import LogEntry
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate, TruncMonth
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View

from analytics.models import UsageEvent
from bookings.models import Booking
from payments.models import Payment
from services.models import Service, StaffProfile, Vendor


def _scope(request, city_path):
    """Return a Q filter scoped to the staff user's location via the given city_path."""
    if request.user.is_superuser:
        return Q()
    try:
        profile = request.user.staff_profile
    except Exception:
        return Q(pk__in=[])
    kwargs = profile.filter_kwargs(city_path)
    return Q(**kwargs) if kwargs else Q()


@method_decorator(staff_member_required, name='dispatch')
class DashboardView(View):

    def get(self, request):
        today = date.today()
        month_start = today.replace(day=1)
        week_start = today - timedelta(days=today.weekday())
        last_30 = today - timedelta(days=29)

        bookings_qs = Booking.objects.filter(_scope(request, 'service__city'))
        services_qs = Service.objects.filter(_scope(request, 'city'))
        vendors_qs  = Vendor.objects.filter(_scope(request, 'city'))
        payments_qs = Payment.objects.filter(_scope(request, 'booking__service__city'))

        # ── Booking status counts ─────────────────────────────────────────────
        status_counts = bookings_qs.aggregate(
            total=Count('id'),
            pending=Count('id', filter=Q(status=Booking.STATUS_PENDING)),
            confirmed=Count('id', filter=Q(status=Booking.STATUS_CONFIRMED)),
            completed=Count('id', filter=Q(status=Booking.STATUS_COMPLETED)),
            cancelled=Count('id', filter=Q(status=Booking.STATUS_CANCELLED)),
        )

        # ── Period counts ─────────────────────────────────────────────────────
        period_counts = bookings_qs.aggregate(
            today=Count('id', filter=Q(created_at__date=today)),
            this_week=Count('id', filter=Q(created_at__date__gte=week_start)),
            this_month=Count('id', filter=Q(created_at__date__gte=month_start)),
        )

        # ── Revenue ───────────────────────────────────────────────────────────
        revenue = bookings_qs.exclude(
            status=Booking.STATUS_CANCELLED
        ).aggregate(
            total_value=Sum('total_amount'),
            advance_collected=Sum('advance_amount'),
        )
        total_value = revenue['total_value'] or 0
        advance_collected = revenue['advance_collected'] or 0
        balance_outstanding = total_value - advance_collected

        # Payments — captured vs refunded
        payment_stats = payments_qs.aggregate(
            paid=Sum('amount', filter=Q(status=Payment.STATUS_CAPTURED)),
            refunded=Sum('amount', filter=Q(status=Payment.STATUS_REFUNDED)),
            failed=Count('id', filter=Q(status=Payment.STATUS_FAILED)),
        )
        paid = payment_stats['paid'] or 0
        refunded = payment_stats['refunded'] or 0
        failed_count = payment_stats['failed'] or 0

        # ── Upcoming events ───────────────────────────────────────────────────
        upcoming = (
            bookings_qs
            .filter(event_date__gte=today, status=Booking.STATUS_CONFIRMED)
            .order_by('event_date')
            .select_related('service__city__district__state')[:10]
        )

        # ── Recent bookings ───────────────────────────────────────────────────
        recent_bookings = (
            bookings_qs
            .order_by('-created_at')
            .select_related('service__category', 'service__city__district__state')[:15]
        )

        # ── Daily bookings last 30 days (for chart) ───────────────────────────
        daily_raw = (
            bookings_qs
            .filter(created_at__date__gte=last_30)
            .annotate(day=TruncDate('created_at'))
            .values('day')
            .annotate(count=Count('id'))
            .order_by('day')
        )
        # Fill gaps so chart has a point for every day
        daily_map = {row['day']: row['count'] for row in daily_raw}
        daily_labels = []
        daily_data = []
        for i in range(30):
            d = last_30 + timedelta(days=i)
            daily_labels.append(d.strftime('%d %b'))
            daily_data.append(daily_map.get(d, 0))

        # ── Monthly revenue last 6 months ─────────────────────────────────────
        six_months_ago = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
        six_months_ago = (today.replace(day=1) - timedelta(days=150)).replace(day=1)
        monthly_rev_raw = (
            bookings_qs
            .filter(created_at__date__gte=six_months_ago)
            .exclude(status=Booking.STATUS_CANCELLED)
            .annotate(month=TruncMonth('created_at'))
            .values('month')
            .annotate(total=Sum('total_amount'), advance=Sum('advance_amount'))
            .order_by('month')
        )
        rev_labels = [row['month'].strftime('%b %Y') for row in monthly_rev_raw]
        rev_total = [float(row['total'] or 0) for row in monthly_rev_raw]
        rev_advance = [float(row['advance'] or 0) for row in monthly_rev_raw]

        # ── Top services by booking count ─────────────────────────────────────
        top_services = (
            services_qs
            .annotate(
                booking_count=Count('bookings'),
                confirmed_count=Count('bookings', filter=Q(bookings__status=Booking.STATUS_CONFIRMED)),
            )
            .order_by('-booking_count')[:8]
        )

        # ── Audit log ─────────────────────────────────────────────────────────
        log_qs = LogEntry.objects.select_related('user', 'content_type').order_by('-action_time')
        if not request.user.is_superuser:
            log_qs = log_qs.filter(user=request.user)
        audit_log = log_qs[:20]

        # ── Catalog counts ────────────────────────────────────────────────────
        catalog = {
            'services': services_qs.count(),
            'active_services': services_qs.filter(is_active=True).count(),
            'vendors': vendors_qs.count(),
        }

        # ── Usage analytics (superusers only — app-wide, not location-scoped) ──
        usage_platforms = [
            UsageEvent.PLATFORM_WEB, UsageEvent.PLATFORM_ANDROID, UsageEvent.PLATFORM_IOS,
        ]
        usage_labels = []
        usage_series = {p: [] for p in usage_platforms}
        recent_usage_events = []
        platform_devices = []
        usage_totals = {'total_devices': 0, 'events_today': 0, 'events_this_week': 0}

        if request.user.is_superuser:
            usage_qs = UsageEvent.objects.all()

            usage_totals = usage_qs.aggregate(
                events_today=Count('id', filter=Q(created_at__date=today)),
                events_this_week=Count('id', filter=Q(created_at__date__gte=week_start)),
            )
            usage_totals['total_devices'] = usage_qs.values('device_id').distinct().count()

            platform_devices = list(
                usage_qs.values('platform')
                .annotate(devices=Count('device_id', distinct=True), events=Count('id'))
                .order_by('-devices')
            )

            daily_usage_raw = (
                usage_qs.filter(created_at__date__gte=last_30)
                .annotate(day=TruncDate('created_at'))
                .values('day', 'platform')
                .annotate(count=Count('id'))
            )
            daily_usage_map = {}
            for row in daily_usage_raw:
                daily_usage_map[(row['day'], row['platform'])] = row['count']
            for i in range(30):
                d = last_30 + timedelta(days=i)
                usage_labels.append(d.strftime('%d %b'))
                for p in usage_platforms:
                    usage_series[p].append(daily_usage_map.get((d, p), 0))

            recent_usage_events = list(usage_qs.order_by('-created_at')[:15])

        # ── Location label for heading ────────────────────────────────────────
        if request.user.is_superuser:
            scope_label = 'All Locations'
        else:
            try:
                scope_label = request.user.staff_profile.location_label
            except Exception:
                scope_label = 'Your Region'

        ctx = {
            # meta
            'title': 'Dashboard',
            'scope_label': scope_label,
            'today': today,
            # status
            **status_counts,
            **period_counts,
            # revenue
            'total_value': total_value,
            'advance_collected': advance_collected,
            'balance_outstanding': balance_outstanding,
            'paid': paid,
            'refunded': refunded,
            'failed_count': failed_count,
            # lists
            'upcoming': upcoming,
            'recent_bookings': recent_bookings,
            'top_services': top_services,
            'audit_log': audit_log,
            # catalog
            'catalog': catalog,
            # chart JSON
            'daily_labels_json': json.dumps(daily_labels),
            'daily_data_json': json.dumps(daily_data),
            'rev_labels_json': json.dumps(rev_labels),
            'rev_total_json': json.dumps(rev_total),
            'rev_advance_json': json.dumps(rev_advance),
            # usage analytics
            'usage_totals': usage_totals,
            'platform_devices': platform_devices,
            'recent_usage_events': recent_usage_events,
            'usage_labels_json': json.dumps(usage_labels),
            'usage_web_json': json.dumps(usage_series[UsageEvent.PLATFORM_WEB]),
            'usage_android_json': json.dumps(usage_series[UsageEvent.PLATFORM_ANDROID]),
            'usage_ios_json': json.dumps(usage_series[UsageEvent.PLATFORM_IOS]),
            'platform_labels_json': json.dumps([p['platform'] for p in platform_devices]),
            'platform_devices_json': json.dumps([p['devices'] for p in platform_devices]),
        }
        ctx.update(admin.site.each_context(request))
        return render(request, 'admin/dashboard.html', ctx)
