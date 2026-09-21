import secrets
import string

from django.db import migrations, models

_CHARS = (string.ascii_uppercase.replace('I', '').replace('O', '')
          + string.digits.replace('0', '').replace('1', ''))


def _generate():
    return 'AB-' + ''.join(secrets.choice(_CHARS) for _ in range(8))


def populate_confirmation_numbers(apps, schema_editor):
    Booking = apps.get_model('bookings', 'Booking')
    seen = set()
    for booking in Booking.objects.all():
        code = _generate()
        while code in seen:
            code = _generate()
        seen.add(code)
        booking.confirmation_number = code
        booking.save(update_fields=['confirmation_number'])


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0002_email_workflow'),
    ]

    operations = [
        # 1. Add nullable first so existing rows are valid
        migrations.AddField(
            model_name='booking',
            name='confirmation_number',
            field=models.CharField(blank=True, max_length=20, default=''),
            preserve_default=False,
        ),
        # 2. Populate existing rows
        migrations.RunPython(populate_confirmation_numbers, migrations.RunPython.noop),
        # 3. Make unique + non-nullable
        migrations.AlterField(
            model_name='booking',
            name='confirmation_number',
            field=models.CharField(max_length=20, unique=True),
        ),
    ]
