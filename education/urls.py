from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("<slug:slug>/", views.location_map, name="location_map"),
]