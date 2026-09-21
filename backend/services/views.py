from django.shortcuts import render, get_object_or_404
from django.db.models import Count, Q, F
from .models import Category, Service, AttributeDefinition, Country, State, District, City


def _category_loc_filter(country_id, state_id):
    """Builds a Count filter for active services matching the given location."""
    f = Q(services__is_active=True)
    if state_id:
        f &= Q(services__city__district__state_id=state_id)
    elif country_id:
        f &= Q(services__city__district__state__country_id=country_id)
    return f


def home(request):
    pref_country_id = request.COOKIES.get('ab_country', '')
    pref_state_id = request.COOKIES.get('ab_state', '')

    categories = Category.objects.filter(is_active=True).annotate(
        filtered_count=Count('services', filter=_category_loc_filter(pref_country_id, pref_state_id))
    )
    from django.db.models import Avg
    from reviews.models import Review

    featured = Service.objects.filter(is_active=True, is_featured=True).select_related(
        'vendor', 'category', 'city__district__state__country'
    ).annotate(
        avg_rating=Avg(
            'reviews__rating',
            filter=Q(reviews__status=Review.STATUS_APPROVED),
        ),
        review_count=Count(
            'reviews',
            filter=Q(reviews__status=Review.STATUS_APPROVED),
        ),
    )[:6]
    featured_cities = City.objects.filter(is_featured=True, is_active=True).order_by('name')[:6]
    countries = Country.objects.filter(is_active=True)

    return render(request, 'home.html', {
        'categories': categories,
        'featured': featured,
        'featured_cities': featured_cities,
        'countries': countries,
        'pref_country_id': pref_country_id,
        'pref_state_id': pref_state_id,
    })


def service_list(request, category_slug=None):
    from django.db.models import Avg
    from reviews.models import Review

    services = Service.objects.filter(is_active=True).select_related(
        'vendor', 'category', 'city__district__state__country'
    ).annotate(
        avg_rating=Avg(
            'reviews__rating',
            filter=Q(reviews__status=Review.STATUS_APPROVED),
        ),
        review_count=Count(
            'reviews',
            filter=Q(reviews__status=Review.STATUS_APPROVED),
        ),
    )
    category = None
    filterable_attrs = []

    if category_slug:
        category = get_object_or_404(Category, slug=category_slug, is_active=True)
        services = services.filter(category=category)
        filterable_attrs = AttributeDefinition.objects.filter(
            category=category, is_filterable=True
        )

    # ── Location filters (URL params take priority; fall back to cookie pref) ──
    pref_country_id = request.COOKIES.get('ab_country', '')
    pref_state_id = request.COOKIES.get('ab_state', '')
    # Use `in` not `.get()` so an explicit empty submit ("All Countries") clears the cookie pref
    has_any_location_param = any(k in request.GET for k in ('country', 'state', 'district', 'city'))

    country_id = request.GET.get('country') or (pref_country_id if not has_any_location_param else '')
    state_id = request.GET.get('state') or (pref_state_id if not has_any_location_param else '')
    district_id = request.GET.get('district')
    city_id = request.GET.get('city')

    if country_id:
        services = services.filter(city__district__state__country_id=country_id)
    if state_id:
        services = services.filter(city__district__state_id=state_id)
    if district_id:
        services = services.filter(city__district_id=district_id)
    if city_id:
        services = services.filter(city_id=city_id)

    # ── Text search ───────────────────────────────────────────────────────────
    q = request.GET.get('q', '').strip()
    if q:
        services = services.filter(
            Q(name__icontains=q) |
            Q(vendor__name__icontains=q) |
            Q(city__name__icontains=q) |
            Q(city__district__name__icontains=q) |
            Q(address__icontains=q)
        )

    # ── Hall type filter (for banquet halls) ──────────────────────────────────
    hall_type = request.GET.get('hall_type')
    if hall_type == 'ac':
        services = services.filter(
            attribute_values__attribute__slug='ac-hall',
            attribute_values__value_boolean=True
        )
    elif hall_type == 'non_ac':
        services = services.filter(
            attribute_values__attribute__slug='non-ac-hall',
            attribute_values__value_boolean=True
        )

    # ── Capacity filter ───────────────────────────────────────────────────────
    min_capacity = request.GET.get('min_capacity')
    if min_capacity:
        services = services.filter(
            attribute_values__attribute__slug='venue-capacity',
            attribute_values__value_number__gte=min_capacity
        )

    sort = request.GET.get('sort', '')
    if sort == 'price_asc':
        services = services.order_by('base_price')
    elif sort == 'price_desc':
        services = services.order_by('-base_price')
    else:
        services = services.order_by('-is_featured', '-created_at')

    services = services.distinct()

    # ── Location dropdowns ────────────────────────────────────────────────────
    countries = Country.objects.filter(is_active=True)
    states = State.objects.filter(is_active=True)
    districts = District.objects.filter(is_active=True)
    cities = City.objects.filter(is_active=True)
    if country_id:
        states = states.filter(country_id=country_id)
        districts = districts.filter(state__country_id=country_id)
        cities = cities.filter(district__state__country_id=country_id)
    if state_id:
        districts = districts.filter(state_id=state_id)
        cities = cities.filter(district__state_id=state_id)
    if district_id:
        cities = cities.filter(district_id=district_id)

    loc_categories = Category.objects.filter(is_active=True).annotate(
        filtered_count=Count('services', filter=_category_loc_filter(country_id, state_id))
    )

    return render(request, 'services/list.html', {
        'services': services,
        'category': category,
        'categories': loc_categories,
        'filterable_attrs': filterable_attrs,
        'countries': countries,
        'states': states,
        'districts': districts,
        'cities': cities,
        'selected_country': country_id,
        'selected_state': state_id,
        'selected_district': district_id,
        'selected_city': city_id,
        'pref_country_id': pref_country_id,
        'pref_state_id': pref_state_id,
        'q': q,
        'sort': sort,
        'hall_type': hall_type or '',
        'min_capacity': min_capacity or '',
    })


def service_detail(request, slug):
    from django.db.models import Avg, Q as Qdb
    from reviews.forms import ReviewForm
    from reviews.models import Review

    service = get_object_or_404(
        Service.objects.annotate(
            avg_rating=Avg(
                'reviews__rating',
                filter=Qdb(reviews__status=Review.STATUS_APPROVED),
            )
        ).select_related('vendor', 'category', 'city__district__state__country'),
        slug=slug, is_active=True,
    )
    Service.objects.filter(pk=service.pk).update(view_count=F('view_count') + 1)
    attr_values = service.attribute_values.select_related('attribute').order_by('attribute__order')
    images = service.images.all()
    booked_dates = list(
        service.bookings.filter(status__in=['pending', 'confirmed']).values_list('event_date', flat=True)
    )
    blocked_dates = list(service.blocked_dates.values_list('date', flat=True))
    unavailable = sorted(set(booked_dates + blocked_dates))

    approved_reviews = Review.objects.filter(
        service=service, status=Review.STATUS_APPROVED
    ).order_by('-created_at')

    return render(request, 'services/detail.html', {
        'service': service,
        'attr_values': attr_values,
        'images': images,
        'unavailable_dates': [d.isoformat() for d in unavailable],
        'reviews': approved_reviews,
        'review_form': ReviewForm(),
    })


def match_location(country_code, state_name):
    """Match an ISO country code and a (fuzzy) state name to active Country/State rows."""
    country_code = (country_code or '').upper()
    state_name = (state_name or '').strip()
    result = {'country_id': None, 'country_name': None, 'state_id': None, 'state_name': None}
    if not country_code:
        return result
    country = Country.objects.filter(code=country_code, is_active=True).first()
    if not country:
        return result
    result['country_id'] = country.id
    result['country_name'] = country.name
    if state_name:
        state = (
            State.objects.filter(country=country, name__iexact=state_name, is_active=True).first()
            or State.objects.filter(country=country, name__icontains=state_name, is_active=True).first()
        )
        if state:
            result['state_id'] = state.id
            result['state_name'] = state.name
    return result


def location_ajax(request):
    """Returns states/districts/cities for a given parent, or matches by code/name."""
    from django.http import JsonResponse

    kind = request.GET.get('kind')
    parent_id = request.GET.get('parent_id')

    if kind == 'states' and parent_id:
        data = list(State.objects.filter(country_id=parent_id, is_active=True).values('id', 'name'))
    elif kind == 'districts' and parent_id:
        data = list(District.objects.filter(state_id=parent_id, is_active=True).values('id', 'name'))
    elif kind == 'cities' and parent_id:
        data = list(City.objects.filter(district_id=parent_id, is_active=True).values('id', 'name'))
    elif kind == 'cities_by_state' and parent_id:
        data = list(City.objects.filter(district__state_id=parent_id, is_active=True).order_by('name').values('id', 'name'))
    elif kind == 'match':
        # Auto-detect: find country by ISO code, then state by name (fuzzy)
        result = match_location(
            request.GET.get('country_code', ''), request.GET.get('state_name', '')
        )
        return JsonResponse(result)
    else:
        data = []
        return JsonResponse({'results': data})

    return JsonResponse({'results': data})


def set_location(request):
    """Saves country/state preference to cookies. Called via POST from the location modal."""
    from django.http import JsonResponse
    from django.views.decorators.http import require_POST

    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    country_id = request.POST.get('country_id', '').strip()
    state_id = request.POST.get('state_id', '').strip()

    response = JsonResponse({'ok': True})
    max_age = 365 * 24 * 60 * 60  # 1 year
    response.set_cookie('ab_country', country_id, max_age=max_age, samesite='Lax')
    response.set_cookie('ab_state', state_id, max_age=max_age, samesite='Lax')
    return response
