from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0005_category_is_active'),
    ]

    operations = [
        migrations.AddField(
            model_name='vendor',
            name='notify_on_booking',
            field=models.BooleanField(
                default=False,
                help_text='Send email to this vendor when a booking is confirmed or cancelled.',
            ),
        ),
    ]
