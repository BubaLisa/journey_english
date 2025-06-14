from django.urls import path
from . import views
from .views import register


urlpatterns = [
    path("", views.index, name="index"),
    path('register/', views.register, name='register'),
    path('login/',    views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),


    path("<slug:slug>/", views.location_map, name="location_map"),
    path("well/toss/", views.well_toss_view, name="well_toss"),

    path("level/<slug:slug>/", views.level_detail, name="level_detail"),
    path("level/<slug:slug>/step/<int:step>/", views.level_detail, name="level_detail_step"),
    path("level/trial/<slug:slug>/<int:step>/", views.level_trial, name="level_trial"),
    path("level/<slug:slug>/boss/", views.level_boss, name="level_boss"),
    path("level/<slug:slug>/fail/", views.level_fail, name="level_fail"),
]