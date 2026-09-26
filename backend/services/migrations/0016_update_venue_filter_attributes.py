from django.db import migrations

# Venue Type: "Lawn / Outdoor" and "Hotel" removed from the sidebar checkbox list.
NEW_VENUE_TYPE_CHOICES = 'Banquet Hall,Convention Center,Resort'
OLD_VENUE_TYPE_CHOICES = 'Banquet Hall,Lawn / Outdoor,Convention Center,Resort,Hotel'

# New top-level Amenities checkbox. 'in-house-catering' is intentionally left
# out here — it already exists (created in migration 0015) and is reused as
# the first item of the new "Other Services → In-house" group instead of
# being duplicated.
NEW_AMENITY_ATTRS = [
    ('rooms', 'Rooms'),
]

# "Other Services" sidebar section: In-house / Outside sub-groups.
OTHER_SERVICES_ATTRS = [
    # ('in-house-catering' already exists from migration 0015; re-labelled below)
    ('inhouse-decoration', 'In-house Decoration'),
    ('inhouse-event-management', 'In-house Event Management'),
    ('inhouse-priests', 'In-house Priests'),
    ('inhouse-music', 'In-house Music'),
    ('inhouse-dance-floor', 'In-house Dance Floor'),
    ('outside-catering', 'Outside Catering'),
    ('outside-decoration', 'Outside Decoration'),
    ('outside-music', 'Outside Music'),
    ('outside-dancefloor', 'Outside Dancefloor'),
    ('outside-event-management', 'Outside Event Management'),
]


def update_venue_filter_attributes(apps, schema_editor):
    Category = apps.get_model('services', 'Category')
    AttributeDefinition = apps.get_model('services', 'AttributeDefinition')

    category = Category.objects.filter(slug='banquet_hall').first()
    if category is None:
        return

    # Trim the Venue Type choice list (existing rows using a removed choice
    # simply stop matching any sidebar checkbox — their data isn't deleted).
    AttributeDefinition.objects.filter(category=category, slug='venue-type').update(
        choices=NEW_VENUE_TYPE_CHOICES
    )

    # 'outdoor-lawn' is no longer used by any sidebar section; drop it so it
    # doesn't linger as an orphaned filterable attribute.
    AttributeDefinition.objects.filter(category=category, slug='outdoor-lawn').delete()

    for order, (slug, name) in enumerate(NEW_AMENITY_ATTRS, start=10):
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

    # Re-label the existing 'in-house-catering' attribute for its new home
    # under "Other Services → In-house" (data/relations are unaffected).
    AttributeDefinition.objects.filter(category=category, slug='in-house-catering').update(
        name='In-house Catering'
    )

    for order, (slug, name) in enumerate(OTHER_SERVICES_ATTRS, start=20):
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


def revert_venue_filter_attributes(apps, schema_editor):
    Category = apps.get_model('services', 'Category')
    AttributeDefinition = apps.get_model('services', 'AttributeDefinition')

    category = Category.objects.filter(slug='banquet_hall').first()
    if category is None:
        return

    AttributeDefinition.objects.filter(category=category, slug='venue-type').update(
        choices=OLD_VENUE_TYPE_CHOICES
    )
    AttributeDefinition.objects.get_or_create(
        category=category,
        slug='outdoor-lawn',
        defaults={'name': 'Outdoor Lawn', 'data_type': 'boolean', 'is_filterable': True, 'order': 5},
    )
    slugs = [slug for slug, _ in NEW_AMENITY_ATTRS] + [slug for slug, _ in OTHER_SERVICES_ATTRS]
    AttributeDefinition.objects.filter(category=category, slug__in=slugs).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0015_venue_filter_attributes'),
    ]

    operations = [
        migrations.RunPython(update_venue_filter_attributes, revert_venue_filter_attributes),
    ]