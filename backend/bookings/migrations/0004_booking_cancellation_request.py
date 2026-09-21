from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0003_booking_confirmation_number'),
    ]

    operations = [
        migrations.AddField(
            model_name='booking',
            name='cancellation_requested',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='booking',
            name='cancellation_request_reason',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='booking',
            name='cancellation_requested_at',
            field=models.DateTimeField(null=True, blank=True),
        ),
        # Extend email_type max_length to accommodate new type names
        migrations.AlterField(
            model_name='emaillog',
            name='email_type',
            field=models.CharField(
                max_length=30,
                choices=[
                    ('booking_received', 'Booking Received (customer)'),
                    ('admin_notify', 'New Booking Notification (admin)'),
                    ('booking_approved', 'Booking Approved (customer)'),
                    ('booking_cancelled', 'Booking Cancelled (customer)'),
                    ('cancel_request_customer', 'Cancellation Request (customer)'),
                    ('cancel_request_admin', 'Cancellation Request (admin)'),
                ],
            ),
        ),
    ]
