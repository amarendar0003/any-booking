def customer_identity(request):
    """Expose the customer's session-based identity (set by a successful
    'Find My Booking' lookup) to every template, so the navbar can switch
    between 'Find My Booking' and 'My Bookings'.
    """
    phone = request.session.get('customer_phone')
    name = request.session.get('customer_name', '')
    return {
        'customer_logged_in': bool(phone),
        'customer_display_name': name,
    }