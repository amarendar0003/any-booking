from django.urls import path

from . import views

urlpatterns = [
    path('login/', views.vendor_login_view, name='vendor_login'),
    path('logout/', views.vendor_logout_view, name='vendor_logout'),
    path('dashboard/', views.vendor_dashboard, name='vendor_dashboard'),
    path('bookings/', views.vendor_bookings, name='vendor_bookings'),
    path('bookings/<int:booking_id>/', views.vendor_booking_detail, name='vendor_booking_detail'),
    path('bookings/<int:booking_id>/approve/', views.vendor_approve_booking, name='vendor_approve_booking'),
    path('bookings/<int:booking_id>/cancel/', views.vendor_cancel_booking, name='vendor_cancel_booking'),
    path('services/<int:service_id>/edit/', views.vendor_edit_service, name='vendor_edit_service'),
    path('reports/', views.vendor_reports, name='vendor_reports'),
    path('profile/', views.vendor_profile, name='vendor_profile'),
]