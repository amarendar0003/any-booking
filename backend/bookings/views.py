from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from services.models import Service
from .models import Booking, BlockedDate
from .forms import BookingForm
import json


def _get_active_terms(service):
    """Return active TermsOfUse queryset applicable to this service (site-wide + service-specific)."""
    from terms.models import TermsOfUse
    return TermsOfUse.objects.filter(
        is_active=True
    ).filter(
        Q(scope=TermsOfUse.SCOPE_SITE) | Q(scope=TermsOfUse.SCOPE_SERVICE, service=service)
    ).order_by('scope', 'title')


def _save_terms_acceptances(booking, terms_qs, request):
    from terms.models import TermsAcceptance
    ip = (
        request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
        or request.META.get('REMOTE_ADDR')
    )
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    for terms in terms_qs:
        TermsAcceptance.objects.create(
            booking=booking,
            terms=terms,
            version_at_acceptance=terms.version,
            ip_address=ip or None,
            user_agent=user_agent,
        )


def booking_create(request, service_slug):
    service = get_object_or_404(Service, slug=service_slug, is_active=True)

    booked_dates = list(
        service.bookings.filter(status__in=['pending', 'confirmed']).values_list('event_date', flat=True)
    )
    blocked_dates = list(service.blocked_dates.values_list('date', flat=True))
    unavailable = sorted(set(booked_dates + blocked_dates))

    active_terms = list(_get_active_terms(service))

    if request.method == 'POST':
        form = BookingForm(request.POST)
        terms_error = None

        if active_terms and not request.POST.get('terms_accepted'):
            terms_error = 'You must read and accept the Terms of Use to proceed.'

        if form.is_valid() and not terms_error:
            booking = form.save(commit=False)
            booking.service = service
            booking.total_amount = service.base_price
            booking.save()

            if active_terms:
                _save_terms_acceptances(booking, active_terms, request)

            # Redirect to payment if online payments are enabled for this country
            country = service.city.country if service.city else None
            if country is not None:
                try:
                    from payments.gateways.registry import get_gateway_for_country
                    gateway = get_gateway_for_country(country)
                except Exception:
                    gateway = None
                if gateway is not None:
                    return redirect('initiate_payment', booking_id=booking.pk)

            messages.success(request, 'Booking request submitted! We will contact you shortly.')
            return redirect('booking_confirmation', pk=booking.pk)
    else:
        form = BookingForm()
        terms_error = None

    return render(request, 'bookings/create.html', {
        'service': service,
        'form': form,
        'unavailable_dates': json.dumps([d.isoformat() for d in unavailable]),
        'active_terms': active_terms,
        'terms_error': terms_error,
    })


def booking_confirmation(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    return render(request, 'bookings/confirmation.html', {'booking': booking})


_ACTIVE_STATUSES = [Booking.STATUS_PENDING, Booking.STATUS_CONFIRMED]


def booking_lookup(request):
    """Let customers find their active booking by confirmation number OR last name + phone."""
    results = None
    searched = False
    error = None

    if request.method == 'POST':
        searched = True
        conf_num = request.POST.get('confirmation_number', '').strip().upper()
        last_name = request.POST.get('last_name', '').strip()
        phone = request.POST.get('phone', '').strip()

        base_qs = Booking.objects.filter(
            status__in=_ACTIVE_STATUSES
        ).select_related('service', 'service__city')

        if conf_num:
            results = list(base_qs.filter(confirmation_number__iexact=conf_num))
        elif last_name and phone:
            results = list(base_qs.filter(
                customer_name__icontains=last_name,
                customer_phone__icontains=phone,
            ).order_by('-created_at'))
        else:
            error = 'Enter a confirmation number, or both last name and phone number.'

        if results is not None and len(results) == 0:
            error = 'No active booking found. Only pending and confirmed bookings can be looked up.'

    return render(request, 'bookings/lookup.html', {
        'results': results,
        'searched': searched,
        'error': error,
    })


def booking_cancel_request(request, confirmation_number):
    """Customer-initiated cancellation request for an active booking."""
    from django.utils import timezone

    booking = get_object_or_404(
        Booking,
        confirmation_number__iexact=confirmation_number,
        status__in=_ACTIVE_STATUSES,
    )

    if booking.cancellation_requested:
        return render(request, 'bookings/cancel_request.html', {
            'booking': booking,
            'already_requested': True,
        })

    error = None
    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        if not reason:
            error = 'Please provide a reason for your cancellation request.'
        else:
            booking.cancellation_requested = True
            booking.cancellation_request_reason = reason
            booking.cancellation_requested_at = timezone.now()
            booking.save(update_fields=[
                'cancellation_requested',
                'cancellation_request_reason',
                'cancellation_requested_at',
                'updated_at',
            ])
            try:
                from .emails import send_cancellation_request
                send_cancellation_request(booking)
            except Exception:
                import logging
                logging.getLogger(__name__).exception('Failed to send cancellation request emails for booking %s', booking.pk)

            return render(request, 'bookings/cancel_request.html', {
                'booking': booking,
                'submitted': True,
            })

    return render(request, 'bookings/cancel_request.html', {
        'booking': booking,
        'error': error,
    })


def check_availability(request, service_id):
    date = request.GET.get('date')
    if not date:
        return JsonResponse({'available': False, 'error': 'No date provided'})

    booked = Booking.objects.filter(
        service_id=service_id,
        event_date=date,
        status__in=['pending', 'confirmed']
    ).exists()
    blocked = BlockedDate.objects.filter(service_id=service_id, date=date).exists()

    return JsonResponse({'available': not booked and not blocked})
