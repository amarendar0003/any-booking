from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Booking


@receiver(post_save, sender=Booking)
def on_booking_saved(sender, instance, created, **kwargs):
    if created:
        # Import here to avoid circular imports at module load time
        from .emails import send_booking_received
        try:
            send_booking_received(instance)
        except Exception:
            # Never let an email failure prevent the booking from saving
            import logging
            logging.getLogger(__name__).exception(
                'send_booking_received failed for booking #%s', instance.pk
            )
