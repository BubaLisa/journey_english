from django.urls import path
from . import views
from .views import register


urlpatterns = [
    path("", views.index, name="index"),
    path('register/', views.register, name='register'),
    path('login/',    views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),


    path("<slug:slug>/", views.location_map, name="location_map"),
    path("level/<slug:slug>/", views.level_detail, name="level_detail"),
    path("level/<slug:slug>/step/<int:step>/", views.level_detail, name="level_detail_step"),
    path('levels/<slug:slug>/trial/', views.trial_level_view, name='trial_level'),
]