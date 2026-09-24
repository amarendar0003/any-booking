from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0013_home_background_image'),
    ]

    operations = [
        migrations.AddField(
            model_name='vendor',
            name='registration_number',
            field=models.CharField(
                max_length=100, blank=True,
                help_text='Business / GST / trade license registration number, shown read-only on the vendor profile page.',
            ),
        ),
        migrations.AddField(
            model_name='vendor',
            name='avatar',
            field=models.ImageField(upload_to='vendors/avatars/', blank=True, null=True),
        ),
    ]