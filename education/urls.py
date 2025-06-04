from django.urls import path
from . import views
from .views import register

urlpatterns = [
    path("", views.index, name="index"),
    path('register/', views.register, name='register'),
    path("<slug:slug>/", views.location_map, name="location_map"),
]