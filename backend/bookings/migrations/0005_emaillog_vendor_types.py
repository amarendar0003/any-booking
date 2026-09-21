from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0004_booking_cancellation_request'),
    ]

    operations = [
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
                    ('vendor_confirmed', 'Booking Confirmed (vendor)'),
                    ('vendor_cancelled', 'Booking Cancelled (vendor)'),
                ],
            ),
        ),
    ]
