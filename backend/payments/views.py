from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from bookings.models import Booking
from .models import Payment
from .gateways.registry import get_gateway_for_country
from .gateways.base import GatewayError


def initiate_payment(request, booking_id):
    booking = get_object_or_404(Booking, pk=booking_id)

    if booking.payments.filter(status='captured').exists():
        return redirect('booking_confirmation', pk=booking.pk)

    country = booking.service.city.country if booking.service.city else None
    if country is None:
        return redirect('booking_confirmation', pk=booking.pk)

    try:
        gateway = get_gateway_for_country(country)
    except GatewayError as exc:
        return render(request, 'payments/error.html', {'error': str(exc)})

    if gateway is None:
        return redirect('booking_confirmation', pk=booking.pk)

    try:
        order_data = gateway.create_order(booking)
    except GatewayError as exc:
        return render(request, 'payments/error.html', {'error': str(exc)})

    payment = Payment.objects.create(
        booking=booking,
        gateway=gateway.slug,
        gateway_order_id=order_data['order_id'],
        amount=order_data['amount'],
        currency=order_data['currency'],
    )

    context = {
        'booking': booking,
        'payment': payment,
    }
    context.update(gateway.get_checkout_context(booking, payment))

    return render(request, gateway.checkout_template, context)


@csrf_exempt
def payment_callback(request):
    if request.method != 'POST':
        from django.http import JsonResponse
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    post_data = request.POST.dict()

    # Find the payment via the gateway-agnostic lookup each gateway provides
    # We determine the gateway from the payment record itself.
    # Try each registered gateway's extract_order_id to find the right order.
    from .gateways.registry import GATEWAY_REGISTRY
    gateway_order_id = None
    matched_gateway = None

    for slug, cls in GATEWAY_REGISTRY.items():
        gw = cls()
        oid = gw.extract_order_id(post_data)
        if oid:
            try:
                payment = Payment.objects.get(gateway_order_id=oid, gateway=slug)
                gateway_order_id = oid
                matched_gateway = gw
                break
            except Payment.DoesNotExist:
                continue

    if matched_gateway is None or gateway_order_id is None:
        from django.http import HttpResponseBadRequest
        return HttpResponseBadRequest('Unknown payment order')

    if not matched_gateway.verify_callback(post_data):
        payment.status = Payment.STATUS_FAILED
        payment.save(update_fields=['status', 'updated_at'])
        return render(request, 'payments/failed.html', {'payment': payment})

    payment.status = Payment.STATUS_CAPTURED
    payment.save(update_fields=['status', 'updated_at'])

    matched_gateway.post_capture_hook(payment, post_data)

    booking = payment.booking
    booking.advance_amount = payment.amount
    booking.status = Booking.STATUS_CONFIRMED
    booking.save(update_fields=['advance_amount', 'status'])

    return redirect('booking_confirmation', pk=booking.pk)
