from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0001_initial'),
        ('services', '0005_category_is_active'),
    ]

    operations = [
        # 1. Add gateway field to Payment
        migrations.AddField(
            model_name='payment',
            name='gateway',
            field=models.CharField(
                choices=[
                    ('razorpay', 'Razorpay (India — UPI, Cards, Net Banking)'),
                    ('stripe',   'Stripe (International — Cards)'),
                    ('cashfree', 'Cashfree (India/SEA)'),
                    ('paystack', 'Paystack (Africa)'),
                ],
                default='razorpay',
                max_length=30,
            ),
        ),

        # 2. Add gateway_order_id (nullable first so existing rows work)
        migrations.AddField(
            model_name='payment',
            name='gateway_order_id',
            field=models.CharField(max_length=200, null=True, blank=True),
        ),

        # 3. Copy razorpay_order_id → gateway_order_id for existing rows
        migrations.RunSQL(
            sql='UPDATE payments_payment SET gateway_order_id = razorpay_order_id',
            reverse_sql='UPDATE payments_payment SET razorpay_order_id = gateway_order_id',
        ),

        # 4. Make gateway_order_id non-nullable + unique
        migrations.AlterField(
            model_name='payment',
            name='gateway_order_id',
            field=models.CharField(max_length=200, unique=True),
        ),

        # 5. Add currency field
        migrations.AddField(
            model_name='payment',
            name='currency',
            field=models.CharField(default='INR', max_length=10),
        ),

        # 6. Drop the old razorpay_order_id column
        migrations.RemoveField(
            model_name='payment',
            name='razorpay_order_id',
        ),

        # 7. Create PaymentGatewayConfig model
        migrations.CreateModel(
            name='PaymentGatewayConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('gateway', models.CharField(
                    choices=[
                        ('razorpay', 'Razorpay (India — UPI, Cards, Net Banking)'),
                        ('stripe',   'Stripe (International — Cards)'),
                        ('cashfree', 'Cashfree (India/SEA)'),
                        ('paystack', 'Paystack (Africa)'),
                    ],
                    max_length=30,
                )),
                ('is_enabled', models.BooleanField(
                    default=False,
                    help_text='Enable to redirect customers to the payment gateway after booking. Disable for offline/cash bookings.',
                )),
                ('display_name', models.CharField(
                    blank=True, max_length=100,
                    help_text='Override the gateway label shown to customers (e.g. "Pay Online")',
                )),
                ('notes', models.TextField(blank=True, help_text='Internal notes — not shown to customers')),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('country', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='payment_config',
                    to='services.country',
                )),
            ],
            options={
                'verbose_name': 'Payment Gateway Config',
                'verbose_name_plural': 'Payment Gateway Configs',
                'ordering': ['country__name'],
            },
        ),
    ]
