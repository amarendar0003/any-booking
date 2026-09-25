from django.db import migrations

# Slugs of the boolean amenity attributes used by the venue filter sidebar.
# 'ac-hall' already exists (created in an earlier migration) and is reused
# here rather than duplicated. 'parking-available' has a migration in this
# app's history (0011) but the row is no longer present in the DB, so it's
# safe (and idempotent, via get_or_create) to include it here again.
NEW_AMENITY_ATTRS = [
    ('parking-available', 'Parking'),
    ('power-backup', 'Power Backup'),
    ('in-house-catering', 'In-house Catering'),
    ('outdoor-lawn', 'Outdoor Lawn'),
]

VENUE_TYPE_CHOICES = 'Banquet Hall,Lawn / Outdoor,Convention Center,Resort,Hotel'


def create_venue_filter_attributes(apps, schema_editor):
    Category = apps.get_model('services', 'Category')
    AttributeDefinition = apps.get_model('services', 'AttributeDefinition')

    category = Category.objects.filter(slug='banquet_hall').first()
    if category is None:
        return

    # Venue Type — single-value choice per service, filtered with "is one of
    # the checked options" (OR) semantics, so no schema change is needed.
    AttributeDefinition.objects.get_or_create(
        category=category,
        slug='venue-type',
        defaults={
            'name': 'Venue Type',
            'data_type': 'choice',
            'choices': VENUE_TYPE_CHOICES,
            'is_filterable': True,
            'order': 1,
        },
    )

    for order, (slug, name) in enumerate(NEW_AMENITY_ATTRS, start=2):
        AttributeDefinition.objects.get_or_create(
            category=category,
            slug=slug,
            defaults={
                'name': name,
                'data_type': 'boolean',
                'is_filterable': True,
                'order': order,
            },
        )


def remove_venue_filter_attributes(apps, schema_editor):
    AttributeDefinition = apps.get_model('services', 'AttributeDefinition')
    slugs = ['venue-type'] + [slug for slug, _ in NEW_AMENITY_ATTRS]
    AttributeDefinition.objects.filter(category__slug='banquet_hall', slug__in=slugs).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0014_vendor_registration_number_vendor_avatar'),
    ]

    operations = [
        migrations.RunPython(create_venue_filter_attributes, remove_venue_filter_attributes),
    ]