from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0007_home_redesign'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='vendor',
            name='user',
            field=models.OneToOneField(
                blank=True,
                help_text='Link to a user account for vendor portal login.',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='vendor_profile',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
