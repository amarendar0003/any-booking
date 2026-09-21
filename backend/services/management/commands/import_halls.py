"""
Management command: import banquet hall data from Excel.

Usage:
    python manage.py import_halls path/to/file.xlsx [--clear]
"""
import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify
from services.models import (
    Country, State, District, City,
    Category, AttributeDefinition, RegionalCategoryConfig,
    Vendor, Service, ServiceAttributeValue,
)


HALL_ATTRS = [
    # (name, slug, data_type, unit)
    ('AC Hall', 'ac-hall', 'boolean', ''),
    ('Non AC Hall', 'non-ac-hall', 'boolean', ''),
    ('Venue Capacity', 'venue-capacity', 'number', 'persons'),
    ('Lunch Hall Capacity', 'lunch-hall-capacity', 'number', 'persons'),
    ('AC Rooms', 'ac-rooms', 'number', 'rooms'),
    ('Non AC Rooms', 'non-ac-rooms', 'number', 'rooms'),
]


class Command(BaseCommand):
    help = 'Import banquet hall listings from the provided Excel file'

    def add_arguments(self, parser):
        parser.add_argument('file', type=str, help='Path to the Excel file')
        parser.add_argument('--clear', action='store_true',
                            help='Delete existing banquet hall services before import')

    def handle(self, *args, **options):
        path = options['file']
        try:
            df = pd.read_excel(path, header=0)
        except Exception as e:
            raise CommandError(f'Cannot read Excel file: {e}')

        df.columns = [c.strip() for c in df.columns]
        df = df.dropna(subset=['Venue Name'])

        # ── Country / Category setup ──────────────────────────────────────────
        india, _ = Country.objects.get_or_create(
            code='IN',
            defaults={
                'name': 'India',
                'currency': 'INR',
                'currency_symbol': '₹',
                'phone_code': '+91',
            }
        )

        category, _ = Category.objects.get_or_create(
            slug=Category.BANQUET_HALL,
            defaults={'description': 'Wedding and event function halls'}
        )

        # ── Attribute definitions ─────────────────────────────────────────────
        attr_objs = {}
        for name, slug, dtype, unit in HALL_ATTRS:
            attr, _ = AttributeDefinition.objects.get_or_create(
                category=category, slug=slug,
                defaults={'name': name, 'data_type': dtype, 'unit': unit, 'is_filterable': True}
            )
            attr_objs[slug] = attr

        if options['clear']:
            deleted, _ = Service.objects.filter(category=category).delete()
            self.stdout.write(self.style.WARNING(f'Cleared {deleted} existing banquet hall services'))

        created_count = 0
        skipped_count = 0

        for _, row in df.iterrows():
            venue_name = str(row.get('Venue Name', '')).strip()
            hall_type = str(row.get('Venue hall name', '')).strip()
            venue_num = row.get('Venue Number', 1)
            capacity = self._int(row.get('Venue Capacity'))
            lunch_cap = self._int(row.get('Lunch Hall Capacity'))
            ac_rooms = self._int(row.get('AC Rooms count'))
            non_ac_rooms = self._int(row.get('Non AC Rooms count'))
            address = str(row.get('Address', '')).strip()
            pin = str(row.get('PIN/ZIP code', '')).strip().split('.')[0]
            city_name = str(row.get('City', '')).strip()
            district_name = str(row.get('District', '')).strip()
            state_name = str(row.get('State', '')).strip()
            contact_name = str(row.get('Contact Name', '')).strip()
            contact_phone = str(row.get('Contact number', '')).strip().split('.')[0]

            if not venue_name or not city_name:
                skipped_count += 1
                continue

            # ── Location ──────────────────────────────────────────────────────
            state, _ = State.objects.get_or_create(
                country=india, name=state_name,
                defaults={'code': state_name[:4].upper()}
            )
            district, _ = District.objects.get_or_create(state=state, name=district_name)
            city, _ = City.objects.get_or_create(
                district=district, name=city_name,
                defaults={'pin_code': pin}
            )

            # ── Regional config (country-level, one-time) ─────────────────────
            config, config_created = RegionalCategoryConfig.objects.get_or_create(
                category=category, country=india, state=None,
                defaults={'price_unit_label': 'per event'}
            )
            if config_created:
                config.enabled_attributes.set(attr_objs.values())

            # ── Vendor ────────────────────────────────────────────────────────
            vendor, _ = Vendor.objects.get_or_create(
                name=venue_name,
                defaults={
                    'phone': contact_phone,
                    'city': city,
                    'address': address,
                }
            )

            # ── Service name = venue name + hall type (unique per hall entry) ─
            service_name = f'{venue_name} – {hall_type}'
            if int(venue_num) > 1:
                service_name = f'{venue_name} – {hall_type} #{int(venue_num)}'

            if Service.objects.filter(
                vendor=vendor, name=service_name
            ).exists() and not options['clear']:
                skipped_count += 1
                continue

            service = Service.objects.create(
                vendor=vendor,
                category=category,
                city=city,
                name=service_name,
                address=address,
                pin_code=pin,
                price_unit='per event',
            )

            # ── Attribute values ──────────────────────────────────────────────
            is_ac = 'ac' in hall_type.lower() and 'non' not in hall_type.lower()
            is_non_ac = 'non ac' in hall_type.lower() or 'non-ac' in hall_type.lower()

            attr_values = [
                (attr_objs['ac-hall'], {'value_boolean': is_ac}),
                (attr_objs['non-ac-hall'], {'value_boolean': is_non_ac}),
                (attr_objs['venue-capacity'], {'value_number': capacity}),
                (attr_objs['lunch-hall-capacity'], {'value_number': lunch_cap}),
                (attr_objs['ac-rooms'], {'value_number': ac_rooms}),
                (attr_objs['non-ac-rooms'], {'value_number': non_ac_rooms}),
            ]
            for attr, val_kwargs in attr_values:
                ServiceAttributeValue.objects.create(service=service, attribute=attr, **val_kwargs)

            created_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'Import complete: {created_count} services created, {skipped_count} skipped'
        ))

    @staticmethod
    def _int(val):
        try:
            return int(float(val))
        except (TypeError, ValueError):
            return 0
