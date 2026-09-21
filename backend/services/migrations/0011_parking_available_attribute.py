from django.db import migrations


def create_parking_attribute(apps, schema_editor):
    Category = apps.get_model('services', 'Category')
    AttributeDefinition = apps.get_model('services', 'AttributeDefinition')

    for slug in ('banquet_hall', 'hotels'):
        category = Category.objects.filter(slug=slug).first()
        if category is None:
            continue
        AttributeDefinition.objects.get_or_create(
            category=category,
            slug='parking-available',
            defaults={
                'name': 'Parking Available',
                'data_type': 'boolean',
                'is_filterable': True,
            },
        )


def remove_parking_attribute(apps, schema_editor):
    AttributeDefinition = apps.get_model('services', 'AttributeDefinition')
    AttributeDefinition.objects.filter(slug='parking-available').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0010_service_cancellation_policy_service_discount_percent_and_more'),
    ]

    operations = [
        migrations.RunPython(create_parking_attribute, remove_parking_attribute),
    ]
