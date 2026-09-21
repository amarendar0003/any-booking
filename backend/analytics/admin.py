from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import UsageEvent


@admin.register(UsageEvent)
class UsageEventAdmin(ModelAdmin):
    list_display = ('platform', 'device_id', 'event_type', 'route', 'created_at')
    list_filter = ('platform', 'event_type')
    search_fields = ('device_id', 'route')
    readonly_fields = ('device_id', 'platform', 'app_version', 'event_type', 'route', 'created_at')
    ordering = ('-created_at',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
