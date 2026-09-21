from django.db import migrations


def enable_parking_in_regional_configs(apps, schema_editor):
    AttributeDefinition = apps.get_model('services', 'AttributeDefinition')
    RegionalCategoryConfig = apps.get_model('services', 'RegionalCategoryConfig')

    for attribute in AttributeDefinition.objects.filter(
        slug='parking-available', category__slug__in=('banquet_hall', 'hotels')
    ):
        for config in RegionalCategoryConfig.objects.filter(category=attribute.category):
            config.enabled_attributes.add(attribute)


def disable_parking_in_regional_configs(apps, schema_editor):
    AttributeDefinition = apps.get_model('services', 'AttributeDefinition')
    RegionalCategoryConfig = apps.get_model('services', 'RegionalCategoryConfig')

    for attribute in AttributeDefinition.objects.filter(slug='parking-available'):
        for config in RegionalCategoryConfig.objects.filter(category=attribute.category):
            config.enabled_attributes.remove(attribute)


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0011_parking_available_attribute'),
    ]

    operations = [
        migrations.RunPython(enable_parking_in_regional_configs, disable_parking_in_regional_configs),
    ]
