from django.contrib import admin
from django.contrib import messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User, Group
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline, StackedInline
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm
from .admin_mixins import LocationRestrictedMixin
from .models import (
    Country, State, District, City,
    Category, AttributeDefinition, AttributeLocalName, RegionalCategoryConfig,
    Vendor, VendorStaffUser, Service, ServiceAttributeValue, ServiceImage, StaffProfile,
)


# ── Location ──────────────────────────────────────────────────────────────────

class StateInline(TabularInline):
    model = State
    extra = 1
    fields = ('name', 'code', 'is_active')


class DistrictInline(TabularInline):
    model = District
    extra = 1
    fields = ('name', 'is_active')


class CityInline(TabularInline):
    model = City
    extra = 1
    fields = ('name', 'pin_code', 'is_active', 'is_featured')


@admin.register(Country)
class CountryAdmin(ModelAdmin):
    list_display = ('name', 'code', 'currency', 'currency_symbol', 'phone_code', 'is_active', 'state_count')
    list_editable = ('is_active',)
    search_fields = ('name', 'code')
    inlines = [StateInline]

    def state_count(self, obj):
        return obj.states.count()
    state_count.short_description = 'States'


@admin.register(State)
class StateAdmin(ModelAdmin):
    list_display = ('name', 'code', 'country', 'is_active', 'district_count')
    list_filter = ('country', 'is_active')
    search_fields = ('name', 'code')
    inlines = [DistrictInline]

    def district_count(self, obj):
        return obj.districts.count()
    district_count.short_description = 'Districts'


@admin.register(District)
class DistrictAdmin(ModelAdmin):
    list_display = ('name', 'state', 'is_active', 'city_count')
    list_filter = ('state__country', 'state', 'is_active')
    inlines = [CityInline]

    def city_count(self, obj):
        return obj.cities.count()
    city_count.short_description = 'Cities'


@admin.register(City)
class CityAdmin(ModelAdmin):
    list_display = ('name', 'district', 'state_name', 'country_name', 'pin_code', 'is_active', 'is_featured')
    list_filter = ('district__state__country', 'district__state', 'is_active', 'is_featured')
    list_editable = ('is_featured',)
    search_fields = ('name', 'pin_code')
    fieldsets = (
        ('Details', {
            'fields': ('district', 'name', 'pin_code', 'is_active'),
        }),
        ('Home Page', {
            'description': 'Tick to pin this city on the home page. Upload a photo for the city card.',
            'fields': ('is_featured', 'image'),
        }),
    )

    def state_name(self, obj):
        return obj.state.name
    state_name.short_description = 'State'

    def country_name(self, obj):
        return obj.country.name
    country_name.short_description = 'Country'


# ── Categories & Attributes ───────────────────────────────────────────────────

@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ('display_name', 'slug', 'icon', 'is_active', 'image_preview', 'service_count')
    list_editable = ('is_active',)
    list_filter = ('is_active',)
    fieldsets = (
        ('Details', {
            'fields': ('slug', 'description', 'icon', 'is_active'),
        }),
        ('Home Page', {
            'description': 'Upload a photo to show on the home page category tile.',
            'fields': ('image',),
        }),
    )

    def service_count(self, obj):
        return obj.services.filter(is_active=True).count()
    service_count.short_description = 'Active Services'

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" height="40" style="border-radius:4px"/>', obj.image.url)
        return '—'
    image_preview.short_description = 'Photo'


class AttributeDefinitionInline(TabularInline):
    model = AttributeDefinition
    extra = 3
    fields = ('name', 'slug', 'data_type', 'choices', 'unit', 'is_filterable', 'order')
    prepopulated_fields = {'slug': ('name',)}


class AttributeLocalNameInline(TabularInline):
    model = AttributeLocalName
    extra = 1
    fields = ('country', 'state', 'local_name')


@admin.register(AttributeDefinition)
class AttributeDefinitionAdmin(ModelAdmin):
    list_display = ('name', 'category', 'data_type', 'unit', 'is_filterable', 'order')
    list_filter = ('category', 'data_type', 'is_filterable')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [AttributeLocalNameInline]


@admin.register(RegionalCategoryConfig)
class RegionalCategoryConfigAdmin(ModelAdmin):
    list_display = ('category', 'country', 'state', 'local_display_name', 'price_unit_label', 'attr_count')
    list_filter = ('category', 'country', 'state')
    filter_horizontal = ('enabled_attributes',)
    fieldsets = (
        ('Region', {
            'fields': ('category', 'country', 'state')
        }),
        ('Local Language Label', {
            'description': 'Override the category name and description shown to users in this region.',
            'fields': ('local_display_name', 'local_description'),
        }),
        ('Configuration', {
            'fields': ('price_unit_label', 'enabled_attributes', 'notes')
        }),
    )

    def attr_count(self, obj):
        return obj.enabled_attributes.count()
    attr_count.short_description = 'Enabled Attributes'


# ── Vendors & Services ────────────────────────────────────────────────────────

class VendorStaffUserInline(TabularInline):
    model = VendorStaffUser
    extra = 0
    fields = ('user',)
    verbose_name = 'Staff login'
    verbose_name_plural = 'Staff logins (can approve/cancel/refund bookings, not pricing or photos)'


@admin.register(Vendor)
class VendorAdmin(LocationRestrictedMixin, ModelAdmin):
    list_display = ('name', 'phone', 'email', 'city', 'is_active', 'notify_on_booking', 'service_count')
    list_editable = ('notify_on_booking',)
    list_filter = ('is_active', 'notify_on_booking', 'city__district__state__country', 'city__district__state')
    search_fields = ('name', 'phone', 'city__name')
    readonly_fields = ('portal_status',)
    inlines = [VendorStaffUserInline]
    fieldsets = (
        ('Vendor Details', {
            'fields': ('name', 'phone', 'email', 'address', 'city', 'is_active'),
        }),
        ('Portal Access', {
            'fields': ('user', 'portal_status'),
            'description': (
                'To link an existing account pick it from the dropdown above. '
                'To create a brand-new login use the link below.'
            ),
        }),
        ('Booking Notifications', {
            'fields': ('notify_on_booking',),
            'description': (
                'When enabled, this vendor receives an email whenever a booking for their '
                'service is confirmed or cancelled. Requires a valid email address above.'
            ),
        }),
    )

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                '<int:vendor_id>/create-user/',
                self.admin_site.admin_view(self.create_user_view),
                name='services_vendor_create_user',
            ),
        ]
        return custom + urls

    def portal_status(self, obj):
        if not obj.pk:
            return '—'
        if obj.user:
            user_url = reverse('admin:auth_user_change', args=[obj.user.pk])
            return format_html(
                '<strong>{}</strong> &nbsp;<a href="{}">(edit user)</a>',
                obj.user.username, user_url,
            )
        create_url = reverse('admin:services_vendor_create_user', args=[obj.pk])
        return format_html('<a href="{}">Create new login account →</a>', create_url)
    portal_status.short_description = 'Current account'

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'user':
            kwargs['queryset'] = User.objects.filter(groups__name='Vendor').order_by('username')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def create_user_view(self, request, vendor_id):
        vendor = get_object_or_404(Vendor, pk=vendor_id)
        error = None

        if request.method == 'POST':
            username = request.POST.get('username', '').strip()
            password = request.POST.get('password', '').strip()
            if not username or not password:
                error = 'Username and password are required.'
            elif User.objects.filter(username=username).exists():
                error = f'The username "{username}" is already taken.'
            else:
                vendor_group, _ = Group.objects.get_or_create(name='Vendor')
                user = User.objects.create_user(username=username, password=password)
                user.groups.add(vendor_group)
                vendor.user = user
                vendor.save(update_fields=['user'])
                messages.success(
                    request,
                    f'Login account "{username}" created and linked to {vendor.name}.',
                )
                return redirect(reverse('admin:services_vendor_change', args=[vendor.pk]))

        context = {
            **self.admin_site.each_context(request),
            'title': f'Create portal login — {vendor.name}',
            'vendor': vendor,
            'error': error,
        }
        return TemplateResponse(
            request, 'admin/services/vendor/create_user.html', context
        )

    def service_count(self, obj):
        return obj.services.count()
    service_count.short_description = 'Services'


class ServiceAttributeValueInline(TabularInline):
    model = ServiceAttributeValue
    extra = 0
    fields = ('attribute', 'value_boolean', 'value_text', 'value_number')


class ServiceImageInline(TabularInline):
    model = ServiceImage
    extra = 2
    fields = ('image', 'caption', 'is_primary', 'order', 'image_preview')
    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" height="60"/>', obj.image.url)
        return '—'
    image_preview.short_description = 'Preview'


@admin.action(description='⭐ Mark selected services as Featured')
def mark_featured(modeladmin, request, queryset):
    updated = queryset.update(is_featured=True)
    modeladmin.message_user(request, f'{updated} service(s) marked as Featured.', messages.SUCCESS)


@admin.action(description='Remove Featured from selected services')
def unmark_featured(modeladmin, request, queryset):
    updated = queryset.update(is_featured=False)
    modeladmin.message_user(request, f'{updated} service(s) removed from Featured.', messages.SUCCESS)


@admin.action(description='✅ Activate selected services')
def activate_services(modeladmin, request, queryset):
    updated = queryset.update(is_active=True)
    modeladmin.message_user(request, f'{updated} service(s) activated.', messages.SUCCESS)


@admin.action(description='🚫 Deactivate selected services')
def deactivate_services(modeladmin, request, queryset):
    updated = queryset.update(is_active=False)
    modeladmin.message_user(request, f'{updated} service(s) deactivated.', messages.WARNING)


@admin.register(Service)
class ServiceAdmin(LocationRestrictedMixin, ModelAdmin):
    list_display = ('name', 'category', 'vendor', 'city_name',
                    'base_price', 'our_price', 'is_active', 'is_featured', 'view_count')
    list_filter = ('category', 'is_active', 'is_featured',
                   'city__district__state__country', 'city__district__state', 'city')
    search_fields = ('name', 'vendor__name', 'city__name', 'address')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('view_count',)
    inlines = [ServiceAttributeValueInline, ServiceImageInline]
    list_editable = ('is_active', 'is_featured')
    actions = [mark_featured, unmark_featured, activate_services, deactivate_services]
    fieldsets = (
        ('Basic Info', {'fields': ('vendor', 'category', 'name', 'slug', 'description')}),
        ('Location', {'fields': ('city', 'address', 'pin_code')}),
        ('Pricing', {
            'fields': ('base_price', 'our_price', 'discount_percent', 'price_unit'),
            'description': '"Hall Owner Price" (base_price) is the vendor\'s own rate and is never '
                            'shown to customers. "Our Price" (our_price) is what customers see and pay '
                            '(after the discount below) — leave it blank to just pass through the Hall '
                            'Owner Price unchanged.',
        }),
        ('Cancellation Policy', {'fields': ('cancellation_policy',)}),
        ('Visibility', {'fields': ('is_active', 'is_featured', 'view_count')}),
    )

    def city_name(self, obj):
        return obj.city.name if obj.city else '—'
    city_name.short_description = 'City'

    def state_name(self, obj):
        return obj.city.state.name if obj.city else '—'
    state_name.short_description = 'State'

    def country_name(self, obj):
        return obj.city.country.name if obj.city else '—'
    country_name.short_description = 'Country'


# ── Staff Profiles & User management ─────────────────────────────────────────

class StaffProfileInline(StackedInline):
    model = StaffProfile
    can_delete = True
    verbose_name = 'Location Scope'
    verbose_name_plural = 'Location Scope'
    fields = ('country', 'state', 'city', 'notes')
    extra = 0

    class Media:
        js = ('js/admin_location_cascade.js',)

    def get_formset(self, request, obj=None, **kwargs):
        # Only superusers can edit staff profiles
        formset = super().get_formset(request, obj, **kwargs)
        if not request.user.is_superuser:
            formset.has_add_permission = lambda *a, **kw: False
            formset.has_change_permission = lambda *a, **kw: False
        return formset


class LocationRestrictedUserAdmin(ModelAdmin, BaseUserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    # Unfold's ModelAdmin defines add_fieldsets=() which shadows BaseUserAdmin's
    # version in the MRO, so we pin it explicitly here and extend with a Role
    # section so admins can assign the Vendor group at creation time.
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Role', {
            'fields': ('groups',),
            'description': 'Add to the "Vendor" group to allow this user to log in at /vendor/login/.',
        }),
    )
    inlines = [StaffProfileInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # Non-superuser staff can only see their own account
        return qs.filter(pk=request.user.pk)

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def get_fieldsets(self, request, obj=None):
        if not request.user.is_superuser:
            return (
                (None, {'fields': ('username', 'password')}),
                ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
            )
        return super().get_fieldsets(request, obj)

    def has_module_perms(self, request):
        # Hides the auth app section from the sidebar for non-superusers
        return request.user.is_superuser


admin.site.unregister(User)
admin.site.register(User, LocationRestrictedUserAdmin)


class GroupAdmin(ModelAdmin):
    def has_module_perms(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


admin.site.unregister(Group)
admin.site.register(Group, GroupAdmin)


@admin.register(StaffProfile)
class StaffProfileAdmin(ModelAdmin):
    list_display = ('user', 'user_email', 'is_active_staff', 'country', 'state', 'city', 'location_label')
    list_filter = ('country', 'state', 'city')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name')
    # country/state/city use plain Unfold selects so the cascade JS can drive them.
    raw_id_fields = ['user']

    class Media:
        js = ('js/admin_location_cascade.js',)
    fieldsets = (
        ('Staff Member', {
            'fields': ('user',),
        }),
        ('Location Scope', {
            'description': (
                'Assign a location to limit this staff member\'s admin access. '
                'City overrides State overrides Country. Leave all blank to grant access to all locations.'
            ),
            'fields': ('country', 'state', 'city'),
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',),
        }),
    )

    def get_queryset(self, request):
        # Only superusers can see/manage staff profiles
        if request.user.is_superuser:
            return super().get_queryset(request)
        return super().get_queryset(request).none()

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email'

    def is_active_staff(self, obj):
        if obj.user.is_superuser:
            return format_html('<span style="color:#b45309;font-weight:bold">⭐ Superadmin</span>')
        if obj.user.is_staff and obj.user.is_active:
            return format_html('<span style="color:#166534">✅ Active</span>')
        return format_html('<span style="color:#991b1b">❌ Inactive</span>')
    is_active_staff.short_description = 'Role'

    def location_label(self, obj):
        return obj.location_label
    location_label.short_description = 'Effective Scope'
