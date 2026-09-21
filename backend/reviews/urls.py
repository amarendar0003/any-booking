from django.urls import path
from . import views

urlpatterns = [
    path('services/<slug:slug>/reviews/add/', views.add_review, name='add_review'),
]
