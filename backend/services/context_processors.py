from .models import Category, Country, State


def nav_categories(request):
    country_id = request.COOKIES.get('ab_country', '')
    state_id = request.COOKIES.get('ab_state', '')

    pref_country = None
    pref_state = None
    if country_id:
        pref_country = Country.objects.filter(pk=country_id).first()
    if state_id:
        pref_state = State.objects.filter(pk=state_id).first()

    # Whether to show the first-visit location modal
    show_location_modal = not country_id

    return {
        'nav_categories': Category.objects.filter(is_active=True),
        'pref_countries': Country.objects.filter(is_active=True).order_by('name'),
        'pref_country': pref_country,
        'pref_state': pref_state,
        'show_location_modal': show_location_modal,
    }
