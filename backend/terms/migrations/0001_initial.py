from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('bookings', '0001_initial'),
        ('services', '0005_category_is_active'),
    ]

    operations = [
        migrations.CreateModel(
            name='TermsOfUse',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('content', models.TextField(help_text='HTML is supported.')),
                ('version', models.CharField(max_length=50, help_text='e.g. v1.0 or 2024-01.')),
                ('scope', models.CharField(
                    choices=[('site', 'Site-wide (all bookings)'), ('service', 'Service-specific')],
                    default='site',
                    max_length=20,
                )),
                ('service', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='terms',
                    to='services.service',
                )),
                ('is_active', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Terms of Use',
                'verbose_name_plural': 'Terms of Use',
                'ordering': ['scope', 'title'],
            },
        ),
        migrations.CreateModel(
            name='TermsAcceptance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('booking', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='terms_acceptances',
                    to='bookings.booking',
                )),
                ('terms', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='acceptances',
                    to='terms.termsofuse',
                )),
                ('version_at_acceptance', models.CharField(max_length=50)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.TextField(blank=True)),
                ('accepted_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Terms Acceptance',
                'verbose_name_plural': 'Terms Acceptances',
                'ordering': ['-accepted_at'],
            },
        ),
    ]
