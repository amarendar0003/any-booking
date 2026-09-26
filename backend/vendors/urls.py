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

    # Service Management (outsourced service vendors)
    path('services-management/', views.vendor_service_management, name='vendor_service_management'),
    path('services-management/add/', views.vendor_add_service_vendor, name='vendor_add_service_vendor'),
    path('services-management/<int:sv_id>/', views.vendor_service_vendor_detail, name='vendor_service_vendor_detail'),
    path('services-management/<int:sv_id>/edit/', views.vendor_edit_service_vendor, name='vendor_edit_service_vendor'),
    path('services-management/<int:sv_id>/log-use/', views.vendor_log_service_vendor_use, name='vendor_log_service_vendor_use'),
    path('services-management/<int:sv_id>/toggle-status/', views.vendor_toggle_service_vendor_status, name='vendor_toggle_service_vendor_status'),
    path('services-management/<int:sv_id>/delete/', views.vendor_delete_service_vendor, name='vendor_delete_service_vendor'),
    path('services-management/<int:sv_id>/toggle-date/', views.vendor_toggle_service_vendor_date, name='vendor_toggle_service_vendor_date'),

    # Staff
    path('staff/', views.vendor_staff, name='vendor_staff'),
    path('staff/add/', views.vendor_add_staff, name='vendor_add_staff'),
    path('staff/<int:staff_id>/edit/', views.vendor_edit_staff, name='vendor_edit_staff'),
    path('staff/<int:staff_id>/delete/', views.vendor_delete_staff, name='vendor_delete_staff'),

    # Gallery
    path('gallery/', views.vendor_gallery, name='vendor_gallery'),
    path('gallery/upload/', views.vendor_upload_gallery_photo, name='vendor_upload_gallery_photo'),
    path('gallery/<int:photo_id>/delete/', views.vendor_delete_gallery_photo, name='vendor_delete_gallery_photo'),
]