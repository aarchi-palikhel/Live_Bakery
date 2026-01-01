# products/urls.py
from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('search/', views.product_search, name='product_search'),
    path('category/<slug:category_slug>/', views.product_list, name='product_list_by_category'),
    
    # Product detail - REMOVED customize_cake from here
    path('<int:product_id>/', views.product_detail, name='product_detail'),
    
    # Optional slug version - keep if you need it
    path('<slug:category_slug>/<slug:product_slug>/', views.product_detail, name='product_detail_slug'),
]