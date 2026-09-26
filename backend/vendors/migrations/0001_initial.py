import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('services', '0016_update_venue_filter_attributes'),
    ]

    operations = [
        migrations.CreateModel(
            name='ServiceVendor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('phone', models.CharField(max_length=20)),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('address', models.TextField(blank=True)),
                ('service_type', models.CharField(choices=[
                    ('catering', 'Catering'),
                    ('decorations', 'Decorations'),
                    ('photography', 'Photography & Videography'),
                    ('music_dj', 'Music / DJ'),
                    ('lighting', 'Lighting'),
                    ('transport', 'Transport'),
                    ('makeup_styling', 'Makeup & Styling'),
                    ('anchoring', 'Anchoring / Emcee'),
                    ('other', 'Other'),
                ], default='other', max_length=30)),
                ('pricing_type', models.CharField(choices=[
                    ('per_plate', 'Per Plate'),
                    ('per_venue', 'Per Venue'),
                ], default='per_plate', max_length=20)),
                ('price', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('rating', models.DecimalField(
                    decimal_places=1, default=0, max_digits=2,
                    validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(5)],
                    help_text='Out of 5',
                )),
                ('times_opted', models.PositiveIntegerField(
                    default=0,
                    help_text='How many times this vendor has outsourced work to this service provider.',
                )),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('vendor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='outsourced_services', to='services.vendor')),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='StaffMember',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('role', models.CharField(blank=True, help_text='e.g. Manager, Server, Coordinator', max_length=100)),
                ('phone', models.CharField(max_length=20)),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('address', models.TextField(blank=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('vendor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='staff_members', to='services.vendor')),
            ],
            options={'ordering': ['name']},
        ),
        migrations.CreateModel(
            name='GalleryPhoto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Reference name for this photo', max_length=200)),
                ('image', models.ImageField(upload_to='vendors/gallery/')),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('vendor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='gallery_photos', to='services.vendor')),
            ],
            options={'ordering': ['-uploaded_at']},
        ),
        migrations.CreateModel(
            name='ServiceVendorBlockedDate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('note', models.CharField(blank=True, max_length=200)),
                ('service_vendor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='blocked_dates', to='vendors.servicevendor')),
            ],
            options={'ordering': ['date']},
        ),
        migrations.AlterUniqueTogether(
            name='servicevendorblockeddate',
            unique_together={('service_vendor', 'date')},
        ),
    ]