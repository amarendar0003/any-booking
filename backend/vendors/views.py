import calendar as cal_module
import json
from datetime import date, timedelta
from functools import wraps

from django.contrib import messages
from django.contrib.auth import login, logout
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from bookings.audit import log_booking_status_change
from bookings.emails import send_booking_approved, send_booking_cancelled
from bookings.models import Booking
from services.models import Service, ServiceImage


def _resolve_vendor_role(user):
    """Returns (vendor, role) for a vendor-portal user, or (None, None).

    Vendor.user (the original OneToOne) is unchanged and always means
    'owner' — VendorStaffUser is a separate, additive model for staff
    logins that can manage bookings but not pricing/photos.
    """
    owner_vendor = getattr(user, 'vendor_profile', None)
    if owner_vendor is not None:
        return owner_vendor, 'owner'
    staff_profile = getattr(user, 'vendor_staff_profile', None)
    if staff_profile is not None:
        return staff_profile.vendor, 'staff'
    return None, None


def vendor_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            # Single entry point: home-page Sign In modal.
            return redirect('/')
        vendor, role = _resolve_vendor_role(request.user)
        if vendor is None:
            logout(request)
            messages.error(request, 'This account is not linked to a vendor.')
            return redirect('/')
        return view_func(request, *args, vendor=vendor, role=role, **kwargs)
    return wrapper


def owner_required(view_func):
    """Like vendor_required, but only the vendor owner may proceed."""
    @vendor_required
    @wraps(view_func)
    def wrapper(request, *args, vendor=None, role=None, **kwargs):
        if role != 'owner':
            messages.error(request, 'Only the vendor owner can do that.')
            return redirect('vendor_dashboard')
        return view_func(request, *args, vendor=vendor, role=role, **kwargs)
    return wrapper


def vendor_login_view(request):
    """Deprecated standalone vendor login page — removed.

    The single login entry point for customers, vendors and vendor staff is
    the home-page nav Sign In modal (POST /accounts/login/, email + password).
    Authenticated vendors are forwarded to their dashboard; everyone else
    goes to the home page.
    """
    if request.user.is_authenticated and _resolve_vendor_role(request.user)[0] is not None:
        return redirect('vendor_dashboard')
    return redirect('/')


def vendor_logout_view(request):
    logout(request)
    return redirect('/')


@vendor_required
def vendor_dashboard(request, vendor=None, role=None):
    services = vendor.services.filter(is_active=True).order_by('name')
    service_ids = list(services.values_list('id', flat=True))

    recent_bookings = (
        Booking.objects
        .filter(service__in=service_ids)
        .select_related('service')
        .order_by('-created_at')[:10]
    )
    pending_count = Booking.objects.filter(service__in=service_ids, status=Booking.STATUS_PENDING).count()
    confirmed_count = Booking.objects.filter(service__in=service_ids, status=Booking.STATUS_CONFIRMED).count()
    cancelled_count = Booking.objects.filter(service__in=service_ids, status=Booking.STATUS_CANCELLED).count()

    today = timezone.localdate()

    # Nearest booking still to come (pending or confirmed), soonest first.
    latest_upcoming_booking = (
        Booking.objects
        .filter(service__in=service_ids, event_date__gte=today)
        .exclude(status=Booking.STATUS_CANCELLED)
        .select_related('service')
        .order_by('event_date', 'event_time')
        .first()
    )

    # Most recently cancelled booking, for the "Cancelled Bookings" card.
    latest_cancelled_booking = (
        Booking.objects
        .filter(service__in=service_ids, status=Booking.STATUS_CANCELLED)
        .select_related('service')
        .order_by('-updated_at')
        .first()
    )

    # Customers asking to cancel a still-active booking — needs vendor review
    # before it can be approved or cancelled.
    cancellation_requests_qs = (
        Booking.objects
        .filter(service__in=service_ids, cancellation_requested=True)
        .exclude(status=Booking.STATUS_CANCELLED)
        .select_related('service')
        .order_by('-cancellation_requested_at')
    )
    cancel_requested_count = cancellation_requests_qs.count()
    cancellation_requests = list(cancellation_requests_qs[:3])

    service_stats = []
    for service in services:
        bookings = Booking.objects.filter(service=service)
        service_stats.append({
            'service': service,
            'view_count': service.view_count,
            'total_bookings': bookings.count(),
            'pending': bookings.filter(status=Booking.STATUS_PENDING).count(),
            'confirmed': bookings.filter(status=Booking.STATUS_CONFIRMED).count(),
            'cancelled': bookings.filter(status=Booking.STATUS_CANCELLED).count(),
            'completed': bookings.filter(status=Booking.STATUS_COMPLETED).count(),
        })

    calendar_ctx = _build_dashboard_calendar(request, service_ids, today)

    return render(request, 'vendors/dashboard.html', {
        'vendor': vendor,
        'role': role,
        'services': services,
        'service_stats': service_stats,
        'recent_bookings': recent_bookings,
        'pending_count': pending_count,
        'confirmed_count': confirmed_count,
        'cancelled_count': cancelled_count,
        'latest_upcoming_booking': latest_upcoming_booking,
        'latest_cancelled_booking': latest_cancelled_booking,
        'cancellation_requests': cancellation_requests,
        'cancel_requested_count': cancel_requested_count,
        **calendar_ctx,
    })


def _build_dashboard_calendar(request, service_ids, today):
    """Build a month grid of booking status + per-day booking detail for the
    vendor dashboard calendar.

    Day status rules (used both for cell coloring and for what the click
    panel shows):
      - booked (red): the date has at least one active (pending/confirmed/
        completed) booking — those are the bookings shown for the day.
      - cancelled (black): the date has no active booking, only cancelled
        one(s), AND the date has already passed — the cancelled booking(s)
        are shown for the day.
      - available (green): everything else — no bookings shown, "available
        to book".
    """
    try:
        cal_year = int(request.GET.get('year', today.year))
        cal_month = int(request.GET.get('month', today.month))
    except (TypeError, ValueError):
        cal_year, cal_month = today.year, today.month

    # Roll over if navigation pushed us outside 1-12.
    if cal_month < 1:
        cal_month, cal_year = 12, cal_year - 1
    elif cal_month > 12:
        cal_month, cal_year = 1, cal_year + 1

    month_bookings = (
        Booking.objects
        .filter(service__in=service_ids, event_date__year=cal_year, event_date__month=cal_month)
        .select_related('service')
        .order_by('event_time', 'created_at')
    )

    bookings_by_day = {}
    for booking in month_bookings:
        bookings_by_day.setdefault(booking.event_date.day, []).append(booking)

    num_days = cal_module.monthrange(cal_year, cal_month)[1]
    day_details = {}

    for day in range(1, num_days + 1):
        day_date = date(cal_year, cal_month, day)
        day_list = bookings_by_day.get(day, [])
        active = [b for b in day_list if b.status != Booking.STATUS_CANCELLED]
        cancelled = [b for b in day_list if b.status == Booking.STATUS_CANCELLED]

        if active:
            day_status = 'booked'
            shown = active
        elif cancelled and day_date < today:
            day_status = 'cancelled'
            shown = cancelled
        else:
            day_status = 'available'
            shown = []

        day_details[day_date.isoformat()] = {
            'status': day_status,
            'bookings': [
                {
                    'id': b.id,
                    'confirmation_number': b.confirmation_number,
                    'customer_name': b.customer_name,
                    'service_name': b.service.name,
                    'status': b.status,
                    'status_display': b.get_status_display(),
                    'is_pending': b.status == Booking.STATUS_PENDING,
                    'event_time': b.event_time.strftime('%I:%M %p').lstrip('0') if b.event_time else '',
                    'guest_count': b.guest_count,
                    'cancellation_reason': b.cancellation_reason,
                    'detail_url': reverse('vendor_booking_detail', args=[b.id]),
                }
                for b in shown
            ],
        }

    weeks = []
    for week in cal_module.Calendar(firstweekday=6).monthdayscalendar(cal_year, cal_month):
        week_days = []
        for day in week:
            if day == 0:
                week_days.append(None)
                continue
            day_date = date(cal_year, cal_month, day)
            week_days.append({
                'day': day,
                'date': day_date.isoformat(),
                'status': day_details[day_date.isoformat()]['status'],
                'is_today': day_date == today,
            })
        weeks.append(week_days)

    prev_month, prev_year = (12, cal_year - 1) if cal_month == 1 else (cal_month - 1, cal_year)
    next_month, next_year = (1, cal_year + 1) if cal_month == 12 else (cal_month + 1, cal_year)

    return {
        'calendar_weeks': weeks,
        'calendar_weekday_labels': ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'],
        'calendar_month_label': date(cal_year, cal_month, 1).strftime('%B %Y'),
        'calendar_prev': {'month': prev_month, 'year': prev_year},
        'calendar_next': {'month': next_month, 'year': next_year},
        'calendar_is_current_month': (cal_year, cal_month) == (today.year, today.month),
        'calendar_day_details': day_details,
    }


@vendor_required
def vendor_bookings(request, vendor=None, role=None):
    service_ids = list(vendor.services.values_list('id', flat=True))
    bookings_qs = (
        Booking.objects
        .filter(service__in=service_ids)
        .select_related('service')
        .order_by('-created_at')
    )

    selected_status = request.GET.get('status', '')
    selected_service = request.GET.get('service', '')
    cancel_requested_filter = request.GET.get('cancel_requested', '')

    if selected_status:
        bookings_qs = bookings_qs.filter(status=selected_status)
    if selected_service:
        bookings_qs = bookings_qs.filter(service_id=selected_service)
    if cancel_requested_filter == '1':
        bookings_qs = bookings_qs.filter(cancellation_requested=True)

    return render(request, 'vendors/bookings.html', {
        'vendor': vendor,
        'role': role,
        'bookings': bookings_qs,
        'services': vendor.services.order_by('name'),
        'status_choices': Booking.STATUS_CHOICES,
        'selected_status': selected_status,
        'selected_service': selected_service,
        'cancel_requested_filter': cancel_requested_filter,
    })


@vendor_required
def vendor_booking_detail(request, booking_id, vendor=None, role=None):
    service_ids = list(vendor.services.values_list('id', flat=True))
    booking = get_object_or_404(Booking, pk=booking_id, service_id__in=service_ids)
    return render(request, 'vendors/booking_detail.html', {
        'vendor': vendor,
        'role': role,
        'booking': booking,
        'refund_choices': Booking.REFUND_CHOICES,
    })


@require_POST
@vendor_required
def vendor_approve_booking(request, booking_id, vendor=None, role=None):
    service_ids = list(vendor.services.values_list('id', flat=True))
    booking = get_object_or_404(Booking, pk=booking_id, service_id__in=service_ids)

    if booking.status != Booking.STATUS_PENDING:
        messages.error(request, f'Booking {booking.confirmation_number} is not pending approval.')
    elif booking.cancellation_requested:
        messages.error(
            request,
            f'Booking {booking.confirmation_number} has a pending cancellation request from the customer — '
            'review it before approving.',
        )
    else:
        booking.status = Booking.STATUS_CONFIRMED
        booking.save(update_fields=['status', 'updated_at'])
        log_booking_status_change(request.user, booking, 'Approved via vendor portal (pending → confirmed)')
        send_booking_approved(booking, sent_by=request.user)
        messages.success(request, f'Booking {booking.confirmation_number} approved and customer notified.')

    next_url = request.POST.get('next')
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return redirect(next_url)
    return redirect('vendor_bookings')


@require_POST
@vendor_required
def vendor_cancel_booking(request, booking_id, vendor=None, role=None):
    """Cancel a booking with refund details — available to owner and staff alike."""
    service_ids = list(vendor.services.values_list('id', flat=True))
    booking = get_object_or_404(Booking, pk=booking_id, service_id__in=service_ids)

    if booking.status == Booking.STATUS_COMPLETED:
        messages.error(request, f'Booking {booking.confirmation_number} is already completed and cannot be cancelled.')
        return redirect('vendor_booking_detail', booking_id=booking.pk)

    refund_type = request.POST.get('refund_type', Booking.REFUND_NONE)
    refund_amount_raw = request.POST.get('refund_amount', '').strip()
    cancellation_reason = request.POST.get('cancellation_reason', '').strip()

    refund_amount = None
    if refund_type == Booking.REFUND_PARTIAL and refund_amount_raw:
        try:
            refund_amount = float(refund_amount_raw)
        except ValueError:
            pass

    booking.status = Booking.STATUS_CANCELLED
    booking.refund_type = refund_type
    booking.refund_amount = refund_amount
    booking.cancellation_reason = cancellation_reason
    booking.save(update_fields=['status', 'refund_type', 'refund_amount', 'cancellation_reason', 'updated_at'])
    log_booking_status_change(request.user, booking, f'Cancelled via vendor portal (refund: {refund_type})')
    send_booking_cancelled(booking, sent_by=request.user)
    messages.success(request, f'Booking {booking.confirmation_number} cancelled and customer notified.')

    return redirect('vendor_bookings')


@owner_required
def vendor_edit_service(request, service_id, vendor=None, role=None):
    """Owner-only: edit the vendor's own asking price and manage photos.

    Deliberately edits base_price ('Hall Owner Price') only — our_price and
    discount_percent are AnyBooking's platform pricing, not the vendor's.
    """
    service = get_object_or_404(Service, pk=service_id, vendor=vendor)

    if request.method == 'POST':
        base_price_raw = request.POST.get('base_price', '').strip()
        price_unit = request.POST.get('price_unit', '').strip()
        try:
            service.base_price = float(base_price_raw)
        except ValueError:
            messages.error(request, 'Enter a valid price.')
            return redirect('vendor_edit_service', service_id=service.pk)
        if price_unit:
            service.price_unit = price_unit
        service.save(update_fields=['base_price', 'price_unit', 'updated_at'])

        new_image = request.FILES.get('new_image')
        if new_image:
            next_order = service.images.count()
            ServiceImage.objects.create(service=service, image=new_image, order=next_order)

        delete_ids = request.POST.getlist('delete_image')
        if delete_ids:
            service.images.filter(pk__in=delete_ids).delete()

        primary_id = request.POST.get('primary_image')
        if primary_id:
            service.images.update(is_primary=False)
            service.images.filter(pk=primary_id).update(is_primary=True)

        messages.success(request, f'{service.name} updated.')
        return redirect('vendor_edit_service', service_id=service.pk)

    return render(request, 'vendors/edit_service.html', {
        'vendor': vendor,
        'role': role,
        'service': service,
        'images': service.images.all(),
    })

# ── Reports ────────────────────────────────────────────────────────────────

def _build_report_buckets(period, today):
    """Returns an ordered list of {label, start, end} date-range buckets
    for the given period ('weekly' | 'monthly' | 'yearly'), most recent last.
    """
    buckets = []

    if period == 'weekly':
        # Last 8 ISO weeks (Mon–Sun), oldest first.
        this_monday = today - timedelta(days=today.weekday())
        for i in range(7, -1, -1):
            start = this_monday - timedelta(weeks=i)
            end = start + timedelta(days=6)
            label = f'{start.strftime("%d %b")}\u2013{end.strftime("%d %b")}'
            buckets.append({'label': label, 'start': start, 'end': end})

    elif period == 'yearly':
        # Last 5 calendar years, oldest first.
        for i in range(4, -1, -1):
            yr = today.year - i
            buckets.append({
                'label': str(yr),
                'start': date(yr, 1, 1),
                'end': date(yr, 12, 31),
            })

    else:  # monthly (default) — last 12 calendar months, oldest first.
        period = 'monthly'
        y, m = today.year, today.month
        months = []
        for _ in range(12):
            months.append((y, m))
            m -= 1
            if m == 0:
                m, y = 12, y - 1
        for yr, mo in reversed(months):
            start = date(yr, mo, 1)
            last_day = cal_module.monthrange(yr, mo)[1]
            end = date(yr, mo, last_day)
            buckets.append({'label': start.strftime('%b %Y'), 'start': start, 'end': end})

    return buckets


@vendor_required
def vendor_reports(request, vendor=None, role=None):
    services = vendor.services.order_by('name')
    service_ids = list(services.values_list('id', flat=True))

    period = request.GET.get('period', 'monthly')
    if period not in ('weekly', 'monthly', 'yearly'):
        period = 'monthly'

    selected_listing = request.GET.get('listing', 'all')
    if selected_listing.isdigit() and int(selected_listing) in service_ids:
        chart_service_ids = [int(selected_listing)]
        selected_listing = str(int(selected_listing))
    else:
        chart_service_ids = service_ids
        selected_listing = 'all'

    today = timezone.localdate()
    buckets = _build_report_buckets(period, today)

    trend_labels, trend_total, trend_confirmed, trend_cancelled, trend_pending = [], [], [], [], []
    for b in buckets:
        qs = Booking.objects.filter(
            service_id__in=chart_service_ids,
            created_at__date__gte=b['start'],
            created_at__date__lte=b['end'],
        )
        trend_labels.append(b['label'])
        trend_total.append(qs.count())
        trend_confirmed.append(qs.filter(status=Booking.STATUS_CONFIRMED).count())
        trend_cancelled.append(qs.filter(status=Booking.STATUS_CANCELLED).count())
        trend_pending.append(qs.filter(status=Booking.STATUS_PENDING).count())

    range_start = buckets[0]['start'] if buckets else today
    range_end = buckets[-1]['end'] if buckets else today

    scope_qs = Booking.objects.filter(
        service_id__in=chart_service_ids,
        created_at__date__gte=range_start,
        created_at__date__lte=range_end,
    )
    status_counts = {
        'confirmed': scope_qs.filter(status=Booking.STATUS_CONFIRMED).count(),
        'pending': scope_qs.filter(status=Booking.STATUS_PENDING).count(),
        'cancelled': scope_qs.filter(status=Booking.STATUS_CANCELLED).count(),
        'completed': scope_qs.filter(status=Booking.STATUS_COMPLETED).count(),
    }
    kpi_total = sum(status_counts.values())
    # Flat booking list for the "click a doughnut slice" popup — the JS
    # filters this client-side by status, so no extra request is needed.
    booking_records = []
    for b in scope_qs.select_related('service').order_by('-created_at'):
        booking_records.append({
            'confirmation_number': b.confirmation_number,
            'customer_name': b.customer_name,
            'customer_email': b.customer_email or '',
            'customer_phone': b.customer_phone,
            'service_name': b.service.name,
            'event_date': b.event_date.strftime('%d %b %Y') if b.event_date else '',
            'event_time': b.event_time.strftime('%I:%M %p').lstrip('0') if b.event_time else '',
            'guest_count': b.guest_count,
            'total_amount': str(b.total_amount),
            'currency_symbol': b.service.currency_symbol,
            'status': b.status,
            'created_at': b.created_at.strftime('%d %b %Y'),
        })

    # Per-listing breakdown — always covers every listing, regardless of the
    # dropdown, so a vendor with several listings sees all of them side by
    # side at a glance.
    listing_rows = []
    for svc in services:
        qs = Booking.objects.filter(
            service=svc, created_at__date__gte=range_start, created_at__date__lte=range_end,
        )
        total = qs.count()
        confirmed = qs.filter(status=Booking.STATUS_CONFIRMED).count()
        cancelled = qs.filter(status=Booking.STATUS_CANCELLED).count()
        pending = qs.filter(status=Booking.STATUS_PENDING).count()
        completed = qs.filter(status=Booking.STATUS_COMPLETED).count()
        booked = confirmed + completed
        listing_rows.append({
            'service': svc,
            'total': total,
            'confirmed': confirmed,
            'cancelled': cancelled,
            'pending': pending,
            'completed': completed,
            'conversion_rate': round(booked / total * 100, 1) if total else None,
        })

    # Average booking value & revenue (confirmed/completed only), listing-wise.
    for row in listing_rows:
        booked_qs = Booking.objects.filter(
            service=row['service'],
            created_at__date__gte=range_start, created_at__date__lte=range_end,
            status__in=[Booking.STATUS_CONFIRMED, Booking.STATUS_COMPLETED],
        )
        total_revenue = sum((b.total_amount for b in booked_qs), start=0)
        count = booked_qs.count()
        row['revenue'] = total_revenue
        row['avg_booking_value'] = round(total_revenue / count, 2) if count else 0
        row['currency_symbol'] = row['service'].currency_symbol

    return render(request, 'vendors/reports.html', {
        'vendor': vendor,
        'role': role,
        'services': services,
        'period': period,
        'selected_listing': selected_listing,
        'kpi_total': kpi_total,
        'kpi_confirmed': status_counts['confirmed'],
        'kpi_cancelled': status_counts['cancelled'],
        'kpi_pending': status_counts['pending'],
        'kpi_completed': status_counts['completed'],
        'listing_rows': listing_rows,
        'range_label': f"{range_start.strftime('%d %b %Y')} \u2013 {range_end.strftime('%d %b %Y')}",
        'trend_labels_json': json.dumps(trend_labels),
        'trend_total_json': json.dumps(trend_total),
        'trend_confirmed_json': json.dumps(trend_confirmed),
        'trend_cancelled_json': json.dumps(trend_cancelled),
        'trend_pending_json': json.dumps(trend_pending),
        'status_labels_json': json.dumps(['Confirmed', 'Pending', 'Cancelled', 'Completed']),
        'status_data_json': json.dumps([
            status_counts['confirmed'], status_counts['pending'],
            status_counts['cancelled'], status_counts['completed'],
        ]),
        'booking_records_json': json.dumps(booking_records),
    })


# ── Profile ───────────────────────────────────────────────────────────────

@vendor_required
def vendor_profile(request, vendor=None, role=None):
    """Read-only vendor profile — owner/staff view their own business details.
    Editing (if ever needed) belongs in the admin, so every field here is
    intentionally read-only.
    """
    return render(request, 'vendors/profile.html', {
        'vendor': vendor,
        'role': role,
    })