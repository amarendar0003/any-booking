"""
Records a CHANGE LogEntry for a booking mutated outside the standard admin
change form. Django only auto-logs edits made through a model's own admin
change page (ModelAdmin.save_model) — bulk admin actions and the vendor
portal's approve view both mutate Booking directly and were previously
invisible in the audit log despite being exactly the "confirm/cancel"
events it's meant to show.
"""
from django.contrib.admin.models import LogEntry, CHANGE
from django.contrib.contenttypes.models import ContentType


def log_booking_status_change(user, booking, message):
    LogEntry.objects.log_action(
        user_id=user.pk,
        content_type_id=ContentType.objects.get_for_model(booking).pk,
        object_id=booking.pk,
        object_repr=str(booking),
        action_flag=CHANGE,
        change_message=message,
    )
