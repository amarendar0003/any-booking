from django.shortcuts import render, get_object_or_404
from django.db.models import Count, Q, F
from .models import Category, Service, AttributeDefinition, Country, State, District, City, HomeBackgroundImage

# ── Venue filter sidebar config (Banquet Hall category only) ──────────────────
# (attribute slug, display label) for each boolean amenity checkbox shown in
# the sidebar. All of these are ServiceAttributeValue booleans, same pattern
# as the existing "AC Hall" attribute.
AMENITY_ATTRS = [
    ('ac-hall', 'AC / Air Conditioned', 'bi-snow2'),
    ('parking-available', 'Parking', 'bi-p-square'),
    ('power-backup', 'Power Backup', 'bi-lightning-charge'),
    ('rooms', 'Rooms', 'bi-door-open'),
]

# Preset capacity ranges for the "Capacity (Guests)" button group.
# Keyed by the value sent in the `capacity` GET param.
CAPACITY_FILTERS = {
    'lt100': Q(attribute_values__value_number__lt=100),
    '100-300': Q(attribute_values__value_number__gte=100, attribute_values__value_number__lte=300),
    '300-500': Q(attribute_values__value_number__gte=300, attribute_values__value_number__lte=500),
    '500-800': Q(attribute_values__value_number__gte=500, attribute_values__value_number__lte=800),
    'gt800': Q(attribute_values__value_number__gt=800),
}
CAPACITY_LABELS = [
    ('any', 'Any'),
    ('lt100', '<100'),
    ('100-300', '100 - 300'),
    ('300-500', '300 - 500'),
    ('500-800', '500 - 800'),
    ('gt800', '>800'),
]

# "Other Services" sidebar section: not a checkbox itself — picking "In-house"
# or "Outside" reveals that group's own checkboxes. Both groups reuse the same
# multi-select GET param (`other_services`) so a single AND-filter loop, like
# the one used for AMENITY_ATTRS, covers both. 'inhouse-catering' is the same
# attribute slug previously listed directly under Amenities.
OTHER_SERVICES_GROUPS = {
    'inhouse': {
        'label': 'In-house',
        'attrs': [
            ('inhouse-catering', 'In-house Catering'),
            ('inhouse-decoration', 'In-house Decoration'),
            ('inhouse-event-management', 'In-house Event Management'),
            ('inhouse-priests', 'In-house Priests'),
            ('inhouse-music', 'In-house Music'),
            ('inhouse-dance-floor', 'In-house Dance Floor'),
        ],
    },
    'outside': {
        'label': 'Outside',
        'attrs': [
            ('outside-catering', 'Outside Catering'),
            ('outside-decoration', 'Outside Decoration'),
            ('outside-event-management', 'Outside Event Management'),
            ('outside-priests', 'Outside Priests'),
            ('outside-music', 'Outside Music'),
            ('outside-dancefloor', 'Outside Dancefloor'),
        ],
    },
}


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
    hero_images = HomeBackgroundImage.objects.all()[:HomeBackgroundImage.MAX_IMAGES]

    return render(request, 'home.html', {
        'categories': categories,
        'featured': featured,
        'featured_cities': featured_cities,
        'countries': countries,
        'pref_country_id': pref_country_id,
        'pref_state_id': pref_state_id,
        'hero_images': hero_images,
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

    # ── Venue filter sidebar (Banquet Hall + "All" categories): venue type,
    # amenities, other services, capacity. Snapshot the queryset *before*
    # these filters so facet counts (how many results each checkbox would
    # give) reflect location/search/hall_type but not the sidebar selections
    # themselves — otherwise checking a box could make its own count (and its
    # siblings') collapse to zero.
    facet_base = services

    venue_type_options = []
    amenities_ctx = []
    other_services_ctx = {}
    capacity_counts = {}
    selected_venue_types = []
    selected_amenities = []
    selected_other_services = []
    capacity = ''
    popular_cities = []

    # Shown on the Banquet Hall category page and on "All Services" (no
    # category selected). Hidden for every other category.
    show_venue_filter = category is None or category.slug == 'banquet_hall'

    if show_venue_filter:
        popular_cities = City.objects.filter(is_featured=True, is_active=True).order_by('name')

        # The venue-filter attribute definitions (venue-type, amenities, other
        # services) always live under the Banquet Hall category, even when
        # this sidebar is being shown on the "All Services" page.
        banquet_category = category or Category.objects.filter(slug='banquet_hall', is_active=True).first()

        # -- Venue Type (multi-select checkboxes, OR'd together) --
        venue_type_attr = AttributeDefinition.objects.filter(category=banquet_category, slug='venue-type').first()
        raw_choices = venue_type_attr.get_choices_list() if venue_type_attr else []
        selected_venue_types = request.GET.getlist('venue_type')
        venue_type_options = [
            {
                'value': choice,
                'label': choice,
                'checked': choice in selected_venue_types,
                'count': facet_base.filter(
                    attribute_values__attribute__slug='venue-type',
                    attribute_values__value_text=choice,
                ).distinct().count(),
            }
            for choice in raw_choices
        ]
        if selected_venue_types:
            services = services.filter(
                attribute_values__attribute__slug='venue-type',
                attribute_values__value_text__in=selected_venue_types,
            )

        # -- Amenities (multi-select checkboxes, AND'd together) --
        selected_amenities = [
            slug for slug in request.GET.getlist('amenities')
            if slug in dict((s, None) for s, _, _ in AMENITY_ATTRS)
        ]
        amenities_ctx = [
            {
                'slug': slug,
                'label': label,
                'icon': icon,
                'checked': slug in selected_amenities,
                'count': facet_base.filter(
                    attribute_values__attribute__slug=slug,
                    attribute_values__value_boolean=True,
                ).distinct().count(),
            }
            for slug, label, icon in AMENITY_ATTRS
        ]
        for slug in selected_amenities:
            services = services.filter(
                attribute_values__attribute__slug=slug,
                attribute_values__value_boolean=True,
            )

        # -- Other Services (multi-select checkboxes, grouped under In-house / Outside) --
        all_other_services_slugs = [
            slug for group in OTHER_SERVICES_GROUPS.values() for slug, _ in group['attrs']
        ]
        selected_other_services = [
            slug for slug in request.GET.getlist('other_services')
            if slug in all_other_services_slugs
        ]
        other_services_ctx = {
            group_key: {
                'label': group['label'],
                'items': [
                    {
                        'slug': slug,
                        'label': label,
                        'checked': slug in selected_other_services,
                        'count': facet_base.filter(
                            attribute_values__attribute__slug=slug,
                            attribute_values__value_boolean=True,
                        ).distinct().count(),
                    }
                    for slug, label in group['attrs']
                ],
                'has_checked': any(slug in selected_other_services for slug, _ in group['attrs']),
            }
            for group_key, group in OTHER_SERVICES_GROUPS.items()
        }
        for slug in selected_other_services:
            services = services.filter(
                attribute_values__attribute__slug=slug,
                attribute_values__value_boolean=True,
            )

        # -- Capacity (single-select preset ranges) --
        capacity = request.GET.get('capacity', '')
        capacity_counts['any'] = facet_base.distinct().count()
        for key, q_filter in CAPACITY_FILTERS.items():
            capacity_counts[key] = facet_base.filter(
                Q(attribute_values__attribute__slug='venue-capacity') & q_filter
            ).distinct().count()
        if capacity in CAPACITY_FILTERS:
            services = services.filter(
                Q(attribute_values__attribute__slug='venue-capacity') & CAPACITY_FILTERS[capacity]
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

    context = {
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
        # Venue filter sidebar
        'venue_type_options': venue_type_options,
        'selected_venue_types': selected_venue_types,
        'amenities_ctx': amenities_ctx,
        'selected_amenities': selected_amenities,
        'other_services_ctx': other_services_ctx,
        'selected_other_services': selected_other_services,
        'capacity': capacity,
        'capacity_display': capacity or 'any',
        'capacity_counts': capacity_counts,
        'capacity_labels': CAPACITY_LABELS,
        'popular_cities': popular_cities,
    }

    # AJAX requests (from the sidebar's live-filter JS) get back just the
    # results grid, so the page doesn't reload on every checkbox click.
    if request.GET.get('ajax') == '1' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'services/_results.html', context)

    return render(request, 'services/list.html', context)


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


def match_location(country_code, state_name, city_name=None):
    """Match an ISO country code and (fuzzy) state/city names to active Country/State/City rows."""
    country_code = (country_code or '').upper()
    state_name = (state_name or '').strip()
    city_name = (city_name or '').strip()
    result = {
        'country_id': None, 'country_name': None,
        'state_id': None, 'state_name': None,
        'city_id': None, 'city_name': None,
    }
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
            if city_name:
                city = (
                    City.objects.filter(
                        district__state=state, name__iexact=city_name, is_active=True,
                    ).first()
                    or City.objects.filter(
                        district__state=state, name__icontains=city_name, is_active=True,
                    ).first()
                )
                if city:
                    result['city_id'] = city.id
                    result['city_name'] = city.name
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
        # Auto-detect: find country by ISO code, then state (and optionally city) by name (fuzzy)
        result = match_location(
            request.GET.get('country_code', ''),
            request.GET.get('state_name', ''),
            request.GET.get('city_name', ''),
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


from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def chatbot_chat(request):
    """
    Receives chat messages from the frontend widget and delegates
    to the GroqChatbotModel in services.chatbot.
    """
    import json
    from django.http import JsonResponse
    from .chatbot import ask_assistant

    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8')) if request.body else {}
    except Exception:
        data = request.POST

    message = data.get('message', '').strip()
    history = data.get('history', [])

    if not message:
        return JsonResponse({'error': 'Message cannot be empty'}, status=400)

    result = ask_assistant(message=message, history=history)
    return JsonResponse(result)