from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'users'

urlpatterns = [
    path('login/', views.custom_login, name='login'),
    path('logout/', views.custom_logout, name='logout'),  # Use custom logout
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),
    path('orders/', views.user_orders, name='orders'),
]