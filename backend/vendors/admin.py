from django.contrib import admin

from .models import ServiceVendor, ServiceVendorBlockedDate, StaffMember, GalleryPhoto


class ServiceVendorBlockedDateInline(admin.TabularInline):
    model = ServiceVendorBlockedDate
    extra = 0


@admin.register(ServiceVendor)
class ServiceVendorAdmin(admin.ModelAdmin):
    list_display = ('name', 'vendor', 'service_type', 'pricing_type', 'price', 'rating', 'times_opted', 'is_active')
    list_filter = ('service_type', 'pricing_type', 'is_active')
    search_fields = ('name', 'phone', 'email', 'vendor__name')
    inlines = [ServiceVendorBlockedDateInline]


@admin.register(StaffMember)
class StaffMemberAdmin(admin.ModelAdmin):
    list_display = ('name', 'vendor', 'role', 'phone', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'phone', 'email', 'vendor__name')


@admin.register(GalleryPhoto)
class GalleryPhotoAdmin(admin.ModelAdmin):
    list_display = ('name', 'vendor', 'uploaded_at')
    search_fields = ('name', 'vendor__name')