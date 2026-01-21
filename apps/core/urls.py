from django.urls import path
from . import views
from core.views import dashboard_api

app_name = 'core'


urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('clear-notification/', views.clear_notification, name='clear_notification'),
    path('api/dashboard/', dashboard_api, name='api_dashboard'),
]
