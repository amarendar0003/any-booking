"""
Management command: seed sample data for all 6 non-banquet-hall categories
and add USA, Canada, UAE with location hierarchies.

Usage:
    python manage.py seed_sample_data
    python manage.py seed_sample_data --clear
"""
from decimal import Decimal
from django.core.management.base import BaseCommand
from services.models import (
    Country, State, District, City,
    Category, AttributeDefinition, AttributeLocalName,
    RegionalCategoryConfig, Vendor, Service, ServiceAttributeValue,
)


# ── Location data ──────────────────────────────────────────────────────────────

COUNTRIES = [
    {
        'name': 'United States',
        'code': 'US',
        'currency': 'USD',
        'currency_symbol': '$',
        'phone_code': '+1',
        'states': [
            {
                'name': 'New York',
                'code': 'NY',
                'districts': [
                    {'name': 'Manhattan', 'cities': ['New York City', 'Brooklyn', 'Queens']},
                    {'name': 'Long Island', 'cities': ['Hempstead', 'Babylon', 'Islip']},
                ],
            },
            {
                'name': 'California',
                'code': 'CA',
                'districts': [
                    {'name': 'Los Angeles County', 'cities': ['Los Angeles', 'Beverly Hills', 'Santa Monica']},
                    {'name': 'San Francisco County', 'cities': ['San Francisco', 'Oakland', 'Berkeley']},
                ],
            },
            {
                'name': 'Texas',
                'code': 'TX',
                'districts': [
                    {'name': 'Harris County', 'cities': ['Houston', 'Pasadena', 'Pearland']},
                    {'name': 'Dallas County', 'cities': ['Dallas', 'Irving', 'Garland']},
                ],
            },
        ],
    },
    {
        'name': 'Canada',
        'code': 'CA',
        'currency': 'CAD',
        'currency_symbol': 'C$',
        'phone_code': '+1',
        'states': [
            {
                'name': 'Ontario',
                'code': 'ON',
                'districts': [
                    {'name': 'Toronto Division', 'cities': ['Toronto', 'Mississauga', 'Brampton']},
                    {'name': 'Ottawa Division', 'cities': ['Ottawa', 'Gatineau', 'Kanata']},
                ],
            },
            {
                'name': 'British Columbia',
                'code': 'BC',
                'districts': [
                    {'name': 'Metro Vancouver', 'cities': ['Vancouver', 'Surrey', 'Burnaby']},
                    {'name': 'Capital Regional', 'cities': ['Victoria', 'Saanich', 'Oak Bay']},
                ],
            },
        ],
    },
    {
        'name': 'United Arab Emirates',
        'code': 'AE',
        'currency': 'AED',
        'currency_symbol': 'د.إ',
        'phone_code': '+971',
        'states': [
            {
                'name': 'Dubai',
                'code': 'DXB',
                'districts': [
                    {'name': 'Bur Dubai', 'cities': ['Downtown Dubai', 'Deira', 'Al Barsha']},
                    {'name': 'Jumeirah', 'cities': ['Jumeirah', 'Palm Jumeirah', 'JBR']},
                ],
            },
            {
                'name': 'Abu Dhabi',
                'code': 'AUH',
                'districts': [
                    {'name': 'Abu Dhabi City', 'cities': ['Abu Dhabi', 'Al Khalidiyah', 'Al Mushrif']},
                    {'name': 'Al Ain', 'cities': ['Al Ain', 'Al Hili', 'Al Mu\'tarid']},
                ],
            },
        ],
    },
]


# ── Attribute definitions per category ────────────────────────────────────────

CATEGORY_ATTRS = {
    'music_band': [
        ('Genre', 'genre', 'text', ''),
        ('Number of Artists', 'num-artists', 'number', 'artists'),
        ('Sound Equipment Included', 'sound-equipment', 'boolean', ''),
        ('Min Hours', 'min-hours', 'number', 'hours'),
        ('Live Performance', 'live-performance', 'boolean', ''),
    ],
    'catering': [
        ('Vegetarian Menu', 'vegetarian', 'boolean', ''),
        ('Non-Vegetarian Menu', 'non-vegetarian', 'boolean', ''),
        ('Vegan Options', 'vegan', 'boolean', ''),
        ('Minimum Guests', 'min-guests', 'number', 'persons'),
        ('Price Per Plate', 'price-per-plate', 'number', ''),
        ('Live Cooking', 'live-cooking', 'boolean', ''),
    ],
    'dancing': [
        ('Dance Style', 'dance-style', 'text', ''),
        ('Group or Solo', 'group-solo', 'text', ''),
        ('Min Duration', 'min-duration', 'number', 'hours'),
        ('Costume Included', 'costume-included', 'boolean', ''),
        ('Number of Performers', 'num-performers', 'number', 'persons'),
    ],
    'priests': [
        ('Religion', 'religion', 'text', ''),
        ('Ceremony Type', 'ceremony-type', 'text', ''),
        ('Language', 'language', 'text', ''),
        ('Home Visit', 'home-visit', 'boolean', ''),
    ],
    'event_management': [
        ('Wedding Planning', 'wedding-planning', 'boolean', ''),
        ('Corporate Events', 'corporate-events', 'boolean', ''),
        ('Decoration', 'decoration', 'boolean', ''),
        ('Photography Included', 'photography', 'boolean', ''),
        ('Minimum Budget', 'min-budget', 'number', ''),
        ('Team Size', 'team-size', 'number', 'persons'),
    ],
    'hotels': [
        ('AC Rooms', 'ac-rooms', 'number', 'rooms'),
        ('Non AC Rooms', 'non-ac-rooms', 'number', 'rooms'),
        ('Swimming Pool', 'swimming-pool', 'boolean', ''),
        ('Gym', 'gym', 'boolean', ''),
        ('Restaurant', 'restaurant', 'boolean', ''),
        ('Free WiFi', 'free-wifi', 'boolean', ''),
        ('Star Rating', 'star-rating', 'number', 'stars'),
    ],
}


# ── Sample services per category ──────────────────────────────────────────────

SERVICES = {
    'music_band': [
        # (country_code, state_name, city_name, vendor_name, service_name, phone, price, attr_values)
        ('IN', 'Telangana', 'Hyderabad', 'Rhythm Kings Band', 'Rhythm Kings – Wedding Special',
         '+91-9876543210', Decimal('50000'),
         {'genre': 'Bollywood & Folk', 'num-artists': 8, 'sound-equipment': True, 'min-hours': 3, 'live-performance': True}),

        ('IN', 'Telangana', 'Hyderabad', 'DJ Beats Events', 'DJ Beats – Classic Hits Night',
         '+91-9123456789', Decimal('25000'),
         {'genre': 'Retro & DJ', 'num-artists': 3, 'sound-equipment': True, 'min-hours': 4, 'live-performance': True}),

        ('US', 'New York', 'New York City', 'Manhattan Jazz Ensemble', 'Manhattan Jazz – Corporate Events',
         '+1-2125551234', Decimal('3000'),
         {'genre': 'Jazz & Blues', 'num-artists': 5, 'sound-equipment': True, 'min-hours': 2, 'live-performance': True}),

        ('US', 'California', 'Los Angeles', 'LA String Quartet', 'LA String Quartet – Wedding Package',
         '+1-3105559876', Decimal('2500'),
         {'genre': 'Classical', 'num-artists': 4, 'sound-equipment': False, 'min-hours': 2, 'live-performance': True}),

        ('AE', 'Dubai', 'Downtown Dubai', 'Desert Beat Band', 'Desert Beat – Arabic & International',
         '+971-501234567', Decimal('8000'),
         {'genre': 'Arabic & Pop', 'num-artists': 6, 'sound-equipment': True, 'min-hours': 3, 'live-performance': True}),

        ('CA', 'Ontario', 'Toronto', 'Toronto Fusion Band', 'Toronto Fusion – Multicultural Events',
         '+1-4165551234', Decimal('2800'),
         {'genre': 'World Music', 'num-artists': 5, 'sound-equipment': True, 'min-hours': 3, 'live-performance': True}),
    ],

    'catering': [
        ('IN', 'Telangana', 'Hyderabad', 'Dum Pukht Caterers', 'Dum Pukht – Hyderabadi Biryani Feast',
         '+91-9988776655', Decimal('850'),
         {'vegetarian': True, 'non-vegetarian': True, 'vegan': False, 'min-guests': 50, 'price-per-plate': 850, 'live-cooking': True}),

        ('IN', 'Telangana', 'Secunderabad', 'Saffron Events Catering', 'Saffron – South Indian Wedding Spread',
         '+91-9876501234', Decimal('600'),
         {'vegetarian': True, 'non-vegetarian': False, 'vegan': True, 'min-guests': 100, 'price-per-plate': 600, 'live-cooking': False}),

        ('US', 'New York', 'Brooklyn', 'Brooklyn Bites Catering', 'Brooklyn Bites – American BBQ Package',
         '+1-7185554321', Decimal('85'),
         {'vegetarian': True, 'non-vegetarian': True, 'vegan': True, 'min-guests': 30, 'price-per-plate': 85, 'live-cooking': True}),

        ('US', 'California', 'San Francisco', 'Bay Area Gourmet', 'Bay Area Gourmet – Farm to Table',
         '+1-4155556789', Decimal('120'),
         {'vegetarian': True, 'non-vegetarian': True, 'vegan': True, 'min-guests': 20, 'price-per-plate': 120, 'live-cooking': True}),

        ('AE', 'Dubai', 'Jumeirah', 'Flavors of Arabia', 'Flavors of Arabia – Arabic Mezze & Grill',
         '+971-504567890', Decimal('350'),
         {'vegetarian': True, 'non-vegetarian': True, 'vegan': False, 'min-guests': 50, 'price-per-plate': 350, 'live-cooking': True}),

        ('CA', 'Ontario', 'Mississauga', 'Maple Leaf Catering', 'Maple Leaf – South Asian Fusion',
         '+1-9055557890', Decimal('65'),
         {'vegetarian': True, 'non-vegetarian': True, 'vegan': True, 'min-guests': 40, 'price-per-plate': 65, 'live-cooking': False}),
    ],

    'dancing': [
        ('IN', 'Telangana', 'Hyderabad', 'Nritya Kala Dance Academy', 'Nritya Kala – Classical Bharatanatyam',
         '+91-9123459876', Decimal('30000'),
         {'dance-style': 'Bharatanatyam', 'group-solo': 'Group', 'min-duration': 1, 'costume-included': True, 'num-performers': 6}),

        ('IN', 'Telangana', 'Hyderabad', 'Bollywood Beats Dance Troupe', 'Bollywood Beats – Filmi Dance Show',
         '+91-9000111222', Decimal('20000'),
         {'dance-style': 'Bollywood', 'group-solo': 'Group', 'min-duration': 1, 'costume-included': True, 'num-performers': 10}),

        ('US', 'New York', 'New York City', 'Broadway Dance Co.', 'Broadway Dance – Wedding Reception Show',
         '+1-2125558765', Decimal('2000'),
         {'dance-style': 'Contemporary', 'group-solo': 'Group', 'min-duration': 1, 'costume-included': True, 'num-performers': 4}),

        ('AE', 'Dubai', 'Palm Jumeirah', 'Dubai Belly Dance Artists', 'Dubai Belly Dance – Gala Evening',
         '+971-556789012', Decimal('2500'),
         {'dance-style': 'Belly Dance', 'group-solo': 'Solo', 'min-duration': 1, 'costume-included': True, 'num-performers': 1}),

        ('CA', 'British Columbia', 'Vancouver', 'Pacific Salsa Dance', 'Pacific Salsa – Latin Fiesta',
         '+1-6045556789', Decimal('1500'),
         {'dance-style': 'Salsa & Latin', 'group-solo': 'Group', 'min-duration': 2, 'costume-included': True, 'num-performers': 4}),
    ],

    'priests': [
        ('IN', 'Telangana', 'Hyderabad', 'Pandit Rajendra Sharma', 'Pandit Rajendra – Hindu Wedding Ceremony',
         '+91-9000222333', Decimal('15000'),
         {'religion': 'Hindu', 'ceremony-type': 'Wedding', 'language': 'Telugu & Sanskrit', 'home-visit': True}),

        ('IN', 'Telangana', 'Hyderabad', 'Maulana Syed Hussain', 'Maulana Syed – Nikah Ceremony',
         '+91-9111222333', Decimal('8000'),
         {'religion': 'Islam', 'ceremony-type': 'Nikah', 'language': 'Urdu & Arabic', 'home-visit': True}),

        ('IN', 'Telangana', 'Secunderabad', 'Father Thomas George', 'Father Thomas – Christian Wedding',
         '+91-9222333444', Decimal('10000'),
         {'religion': 'Christian', 'ceremony-type': 'Wedding', 'language': 'English & Telugu', 'home-visit': False}),

        ('US', 'New York', 'Queens', 'Pandit Suresh Iyer', 'Pandit Suresh – Hindu Ceremonies (USA)',
         '+1-7185551234', Decimal('1200'),
         {'religion': 'Hindu', 'ceremony-type': 'Wedding & Pooja', 'language': 'English & Sanskrit', 'home-visit': True}),

        ('AE', 'Dubai', 'Deira', 'Sheikh Abdulla Al Rashid', 'Sheikh Abdulla – Islamic Ceremonies',
         '+971-523456789', Decimal('1500'),
         {'religion': 'Islam', 'ceremony-type': 'Nikah & Khutbah', 'language': 'Arabic & English', 'home-visit': True}),

        ('CA', 'Ontario', 'Brampton', 'Granthi Singh Khalsa', 'Granthi Singh – Sikh Anand Karaj',
         '+1-9051234567', Decimal('800'),
         {'religion': 'Sikh', 'ceremony-type': 'Anand Karaj', 'language': 'Punjabi & Gurmukhi', 'home-visit': False}),
    ],

    'event_management': [
        ('IN', 'Telangana', 'Hyderabad', 'Dream Events HYD', 'Dream Events – Full Wedding Planning',
         '+91-9333444555', Decimal('200000'),
         {'wedding-planning': True, 'corporate-events': False, 'decoration': True, 'photography': True, 'min-budget': 200000, 'team-size': 15}),

        ('IN', 'Telangana', 'Hyderabad', 'Corporate Edge Events', 'Corporate Edge – Annual Conference Package',
         '+91-9444555666', Decimal('500000'),
         {'wedding-planning': False, 'corporate-events': True, 'decoration': True, 'photography': True, 'min-budget': 500000, 'team-size': 20}),

        ('US', 'California', 'Beverly Hills', 'Beverly Hills Elite Events', 'Beverly Hills Elite – Luxury Wedding',
         '+1-3105551234', Decimal('50000'),
         {'wedding-planning': True, 'corporate-events': False, 'decoration': True, 'photography': True, 'min-budget': 50000, 'team-size': 25}),

        ('US', 'New York', 'New York City', 'NYC Corporate Events', 'NYC Corporate – Gala & Conference',
         '+1-2125550000', Decimal('30000'),
         {'wedding-planning': False, 'corporate-events': True, 'decoration': True, 'photography': False, 'min-budget': 30000, 'team-size': 12}),

        ('AE', 'Dubai', 'Downtown Dubai', 'Al Noor Event Management', 'Al Noor – Luxury Dubai Wedding',
         '+971-526543210', Decimal('150000'),
         {'wedding-planning': True, 'corporate-events': True, 'decoration': True, 'photography': True, 'min-budget': 150000, 'team-size': 30}),

        ('CA', 'Ontario', 'Toronto', 'Toronto Premier Events', 'Toronto Premier – South Asian Wedding',
         '+1-4161234567', Decimal('25000'),
         {'wedding-planning': True, 'corporate-events': False, 'decoration': True, 'photography': True, 'min-budget': 25000, 'team-size': 10}),
    ],

    'hotels': [
        ('IN', 'Telangana', 'Hyderabad', 'The Grand Kakatiya', 'The Grand Kakatiya – Deluxe Package',
         '+91-4023456789', Decimal('8000'),
         {'ac-rooms': 120, 'non-ac-rooms': 0, 'swimming-pool': True, 'gym': True, 'restaurant': True, 'free-wifi': True, 'star-rating': 5}),

        ('IN', 'Telangana', 'Hyderabad', 'Hotel Minerva', 'Hotel Minerva – Business Stay',
         '+91-4034567890', Decimal('3500'),
         {'ac-rooms': 60, 'non-ac-rooms': 20, 'swimming-pool': False, 'gym': True, 'restaurant': True, 'free-wifi': True, 'star-rating': 3}),

        ('US', 'New York', 'New York City', 'Manhattan Grand Hotel', 'Manhattan Grand – City View Suite',
         '+1-2129876543', Decimal('450'),
         {'ac-rooms': 300, 'non-ac-rooms': 0, 'swimming-pool': True, 'gym': True, 'restaurant': True, 'free-wifi': True, 'star-rating': 5}),

        ('US', 'California', 'Santa Monica', 'Pacific Shores Hotel', 'Pacific Shores – Beachfront Stay',
         '+1-3109876543', Decimal('350'),
         {'ac-rooms': 80, 'non-ac-rooms': 0, 'swimming-pool': True, 'gym': True, 'restaurant': True, 'free-wifi': True, 'star-rating': 4}),

        ('AE', 'Dubai', 'Palm Jumeirah', 'Palm Atlantis Suites', 'Palm Atlantis – Luxury Resort',
         '+971-44321234', Decimal('2500'),
         {'ac-rooms': 500, 'non-ac-rooms': 0, 'swimming-pool': True, 'gym': True, 'restaurant': True, 'free-wifi': True, 'star-rating': 5}),

        ('AE', 'Abu Dhabi', 'Abu Dhabi', 'Emirates Palace Residences', 'Emirates Palace – Presidential Suite',
         '+971-25551234', Decimal('3500'),
         {'ac-rooms': 200, 'non-ac-rooms': 0, 'swimming-pool': True, 'gym': True, 'restaurant': True, 'free-wifi': True, 'star-rating': 5}),

        ('CA', 'Ontario', 'Toronto', 'CN Tower Hotel', 'CN Tower Hotel – Downtown Toronto',
         '+1-4169876543', Decimal('280'),
         {'ac-rooms': 150, 'non-ac-rooms': 0, 'swimming-pool': True, 'gym': True, 'restaurant': True, 'free-wifi': True, 'star-rating': 4}),

        ('CA', 'British Columbia', 'Vancouver', 'Pacific Rim Vancouver', 'Pacific Rim – Harbour View',
         '+1-6049876543', Decimal('320'),
         {'ac-rooms': 100, 'non-ac-rooms': 0, 'swimming-pool': False, 'gym': True, 'restaurant': True, 'free-wifi': True, 'star-rating': 4}),
    ],
}


# ── Regional label overrides ───────────────────────────────────────────────────

REGIONAL_LABELS = {
    # (category_slug, country_code, state_name_or_None): local_display_name
    ('priests', 'IN', None): 'Pandit / Priest',
    ('priests', 'AE', None): 'Religious Officiant',
    ('priests', 'US', None): 'Officiant / Celebrant',
    ('priests', 'CA', None): 'Officiant / Celebrant',
    ('catering', 'AE', None): 'Catering & Hospitality',
    ('dancing', 'IN', None): 'Dance Performers',
    ('dancing', 'AE', None): 'Entertainment Dancers',
    ('music_band', 'AE', None): 'Live Entertainment',
    ('event_management', 'AE', None): 'Event Management & Planning',
}


class Command(BaseCommand):
    help = 'Seed sample data for all non-banquet-hall categories and add USA, Canada, UAE'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Delete all non-banquet-hall services before seeding',
        )

    def handle(self, *args, **options):
        if options['clear']:
            non_hall = Service.objects.exclude(category__slug='banquet_hall')
            count, _ = non_hall.delete()
            self.stdout.write(self.style.WARNING(f'Cleared {count} non-banquet-hall services'))

        # ── 1. Countries / States / Districts / Cities ─────────────────────────
        country_objs = {}
        city_index = {}  # (country_code, state_name, city_name) → City

        for cdata in COUNTRIES:
            country, _ = Country.objects.update_or_create(
                code=cdata['code'],
                defaults={
                    'name': cdata['name'],
                    'currency': cdata['currency'],
                    'currency_symbol': cdata['currency_symbol'],
                    'phone_code': cdata['phone_code'],
                },
            )
            country_objs[cdata['code']] = country
            self.stdout.write(f'  Country: {country.name}')

            for sdata in cdata['states']:
                state, _ = State.objects.get_or_create(
                    country=country, name=sdata['name'],
                    defaults={'code': sdata['code']},
                )
                for ddata in sdata['districts']:
                    district, _ = District.objects.get_or_create(
                        state=state, name=ddata['name'],
                    )
                    for city_name in ddata['cities']:
                        city, _ = City.objects.get_or_create(
                            district=district, name=city_name,
                        )
                        city_index[(cdata['code'], sdata['name'], city_name)] = city

        # Ensure Hyderabad and Secunderabad exist under Telangana
        india = Country.objects.get(code='IN')
        telangana, _ = State.objects.get_or_create(
            country=india, name='Telangana', defaults={'code': 'TS'}
        )
        hyd_district, _ = District.objects.get_or_create(state=telangana, name='Hyderabad')
        sec_district, _ = District.objects.get_or_create(state=telangana, name='Secunderabad')
        for city_name, district in [('Hyderabad', hyd_district), ('Secunderabad', sec_district)]:
            city, _ = City.objects.get_or_create(district=district, name=city_name)
            city_index[('IN', 'Telangana', city_name)] = city

        # Index all other existing India cities created by import_halls
        for city in City.objects.select_related('district__state__country'):
            key = (city.country.code, city.state.name, city.name)
            if key not in city_index:
                city_index[key] = city

        # ── 2. Ensure all 7 categories exist ───────────────────────────────────
        for slug, desc in [
            ('music_band', 'Live music and band performances'),
            ('event_management', 'Complete event planning and management'),
            ('catering', 'Food and catering services'),
            ('dancing', 'Dance performances and entertainment'),
            ('priests', 'Religious ceremonies and officiants'),
            ('hotels', 'Accommodation and hospitality'),
            ('banquet_hall', 'Wedding and event function halls'),
        ]:
            Category.objects.get_or_create(slug=slug, defaults={'description': desc})

        # ── 3. Attribute definitions ───────────────────────────────────────────
        attr_index = {}  # (category_slug, attr_slug) → AttributeDefinition
        for cat_slug, attrs in CATEGORY_ATTRS.items():
            category = Category.objects.get(slug=cat_slug)
            for name, slug, dtype, unit in attrs:
                attr, _ = AttributeDefinition.objects.get_or_create(
                    category=category, slug=slug,
                    defaults={'name': name, 'data_type': dtype, 'unit': unit, 'is_filterable': True},
                )
                attr_index[(cat_slug, slug)] = attr

        # ── 4. Regional category configs ───────────────────────────────────────
        for (cat_slug, country_code, state_name), label in REGIONAL_LABELS.items():
            country = country_objs.get(country_code)
            if not country:
                continue
            category = Category.objects.get(slug=cat_slug)
            state = State.objects.filter(country=country, name=state_name).first() if state_name else None
            cfg, _ = RegionalCategoryConfig.objects.get_or_create(
                category=category, country=country, state=state,
                defaults={'local_display_name': label, 'price_unit_label': 'per event'},
            )
            if not cfg.local_display_name:
                cfg.local_display_name = label
                cfg.save()

        # Also create country-level configs for all new countries with all attributes enabled
        for country_code, country in country_objs.items():
            for cat_slug, attrs in CATEGORY_ATTRS.items():
                category = Category.objects.get(slug=cat_slug)
                cfg, _ = RegionalCategoryConfig.objects.get_or_create(
                    category=category, country=country, state=None,
                    defaults={'price_unit_label': 'per event'},
                )
                all_attrs = [attr_index[(cat_slug, a[1])] for a in attrs if (cat_slug, a[1]) in attr_index]
                cfg.enabled_attributes.set(all_attrs)

        # ── 5. Seed services ───────────────────────────────────────────────────
        created = 0
        skipped = 0

        for cat_slug, entries in SERVICES.items():
            category = Category.objects.get(slug=cat_slug)

            for (country_code, state_name, city_name,
                 vendor_name, service_name, phone, price, attr_vals) in entries:

                city = city_index.get((country_code, state_name, city_name))
                if not city:
                    self.stdout.write(
                        self.style.WARNING(f'  Skipping — city not found: {country_code}/{state_name}/{city_name}')
                    )
                    skipped += 1
                    continue

                vendor, _ = Vendor.objects.get_or_create(
                    name=vendor_name,
                    defaults={'phone': phone, 'city': city},
                )

                if Service.objects.filter(vendor=vendor, name=service_name).exists():
                    skipped += 1
                    continue

                service = Service.objects.create(
                    vendor=vendor,
                    category=category,
                    city=city,
                    name=service_name,
                    base_price=price,
                    price_unit='per event',
                    is_active=True,
                )

                for attr_slug, raw_val in attr_vals.items():
                    attr = attr_index.get((cat_slug, attr_slug))
                    if not attr:
                        continue
                    kwargs = {}
                    if attr.data_type == 'boolean':
                        kwargs['value_boolean'] = bool(raw_val)
                    elif attr.data_type == 'number':
                        kwargs['value_number'] = Decimal(str(raw_val))
                    else:
                        kwargs['value_text'] = str(raw_val)
                    ServiceAttributeValue.objects.get_or_create(
                        service=service, attribute=attr, defaults=kwargs
                    )

                created += 1

        self.stdout.write(self.style.SUCCESS(
            f'\nDone: {created} services created, {skipped} skipped (already exist).'
        ))
        self.stdout.write(
            f'Countries added/updated: USA, Canada, UAE (plus existing India)'
        )
