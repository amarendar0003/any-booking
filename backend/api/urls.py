from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

urlpatterns = [
    # Auth
    path('auth/vendor/login/', views.vendor_login, name='api_vendor_login'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='api_token_refresh'),

    # Catalog
    path('categories/', views.CategoryListView.as_view(), name='api_categories'),
    path('countries/', views.CountryListView.as_view(), name='api_countries'),
    path('locations/match/', views.location_match, name='api_location_match'),
    path('states/', views.StateListView.as_view(), name='api_states'),
    path('cities/', views.CityListView.as_view(), name='api_cities'),
    path('cities/featured/', views.FeaturedCityListView.as_view(), name='api_featured_cities'),
    path('services/', views.ServiceListView.as_view(), name='api_services'),
    path('services/<slug:slug>/', views.ServiceDetailView.as_view(), name='api_service_detail'),

    # Bookings (public)
    path('bookings/', views.booking_create, name='api_booking_create'),
    path('bookings/lookup/', views.booking_lookup, name='api_booking_lookup'),
    path('bookings/<str:confirmation_number>/cancel-request/', views.booking_cancel_request, name='api_cancel_request'),

    # Client error reporting (public)
    path('client-errors/', views.report_client_error, name='api_report_client_error'),

    # Usage analytics (public)
    path('usage-events/', views.report_usage_event, name='api_report_usage_event'),

    # Vendor (authenticated)
    path('vendor/dashboard/', views.vendor_dashboard, name='api_vendor_dashboard'),
    path('vendor/bookings/', views.vendor_bookings, name='api_vendor_bookings'),
]
