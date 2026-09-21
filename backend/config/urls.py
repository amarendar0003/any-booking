from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from services.dashboard import DashboardView

admin.site.site_header = 'AnyBooking Admin'
admin.site.site_title = 'AnyBooking'
admin.site.index_title = 'Manage Bookings & Services'

urlpatterns = [
    path('admin/dashboard/', DashboardView.as_view(), name='admin_dashboard'),
    path('admin/', admin.site.urls),
    # REST API (iOS app + future frontends)
    path('api/', include('api.urls')),
    # Web app routes
    path('', include('services.urls')),
    path('bookings/', include('bookings.urls')),
    path('payments/', include('payments.urls')),
    path('', include('reviews.urls')),
    path('vendor/', include('vendors.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
