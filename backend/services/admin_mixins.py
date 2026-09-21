"""
LocationRestrictedMixin — apply to any ModelAdmin to scope querysets
by the logged-in staff user's country/state/city assignment.

Superusers always see everything.
Staff without a StaffProfile see nothing (fail-safe).

Usage:
    class MyAdmin(LocationRestrictedMixin, admin.ModelAdmin):
        city_path = 'city'          # path from model to City FK (default)
"""
from django.contrib import admin


class LocationRestrictedMixin:
    # Subclasses override this to match their model's path to the City FK.
    # e.g. 'city' for Service/Vendor, 'service__city' for Booking/BlockedDate,
    #      'booking__service__city' for Payment.
    city_path = 'city'

    def _get_profile(self, request):
        try:
            return request.user.staff_profile
        except Exception:
            return None

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        profile = self._get_profile(request)
        if profile is None:
            return qs.none()
        loc = profile.filter_kwargs(self.city_path)
        return qs.filter(**loc) if loc else qs

    def has_add_permission(self, request):
        if request.user.is_superuser:
            return super().has_add_permission(request)
        return self._get_profile(request) is not None

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return super().has_change_permission(request, obj)
        profile = self._get_profile(request)
        if profile is None:
            return False
        if obj is None:
            return True
        # Verify the object is within the staff member's location scope
        loc = profile.filter_kwargs(self.city_path)
        if not loc:
            return True
        model = type(obj)
        return model.objects.filter(pk=obj.pk, **loc).exists()

    def has_delete_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)
