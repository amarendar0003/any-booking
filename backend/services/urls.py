from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('services/', views.service_list, name='service_list'),
    path('services/<slug:category_slug>/', views.service_list, name='service_list_by_category'),
    path('service/<slug:slug>/', views.service_detail, name='service_detail'),
    path('ajax/location/', views.location_ajax, name='location_ajax'),
    path('ajax/set-location/', views.set_location, name='set_location'),
]
