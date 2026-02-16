from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_home, name='home'),
    path('analytics/', views.dashboard_analytics, name='analytics'),
    path('products/', views.dashboard_products, name='products'),
    path('orders/', views.dashboard_orders, name='orders'),
    path('export/orders/', views.export_orders_excel, name='export_orders'),
    path('export/products/', views.export_products_excel, name='export_products'),
    path('export/dashboard/', views.export_dashboard_excel, name='export_dashboard'),
]
