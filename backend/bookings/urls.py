from django.urls import path
from . import views

urlpatterns = [
    path('book/<slug:service_slug>/', views.booking_create, name='booking_create'),
    path('confirmation/<int:pk>/', views.booking_confirmation, name='booking_confirmation'),
    path('find/', views.booking_lookup, name='booking_lookup'),
    path('cancel-request/<str:confirmation_number>/', views.booking_cancel_request, name='booking_cancel_request'),
    path('check-availability/<int:service_id>/', views.check_availability, name='check_availability'),
]
