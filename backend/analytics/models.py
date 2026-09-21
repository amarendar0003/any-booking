from django.db import models


class UsageEvent(models.Model):
    """
    A single client-reported usage event (currently just 'app_open' on
    launch) — powers the usage-by-platform section of the admin dashboard.
    device_id is a UUID the client generates once and persists locally
    (SharedPreferences on Flutter); it's an anonymous per-install identifier,
    not a hardware device ID, so it resets on reinstall/browser data clear.
    """

    PLATFORM_WEB = 'web'
    PLATFORM_ANDROID = 'android'
    PLATFORM_IOS = 'ios'
    PLATFORM_OTHER = 'other'

    EVENT_APP_OPEN = 'app_open'

    device_id = models.CharField(max_length=64, db_index=True)
    platform = models.CharField(max_length=20, db_index=True)
    app_version = models.CharField(max_length=40, blank=True)
    event_type = models.CharField(max_length=30, default=EVENT_APP_OPEN)
    route = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['platform', 'created_at']),
            models.Index(fields=['device_id', 'created_at']),
        ]

    def __str__(self):
        return f'{self.platform}:{self.device_id[:8]} @ {self.created_at:%Y-%m-%d %H:%M}'
