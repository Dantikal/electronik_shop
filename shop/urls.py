from django.urls import path
from . import views

app_name = 'shop'

urlpatterns = [
    path('', views.home, name='home'),
    path('products/', views.ProductListView.as_view(), name='product_list'),
    path('product/<slug:slug>/', views.ProductDetailView.as_view(), name='product_detail'),
    path('category/<slug:slug>/', views.CategoryDetailView.as_view(), name='category_detail'),
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/add/<int:product_id>/', views.cart_add, name='cart_add'),
    path('cart/remove/<int:product_id>/', views.cart_remove, name='cart_remove'),
    path('checkout/', views.checkout, name='checkout'),
    path('orders/', views.order_list, name='order_list'),
    path('order/<int:pk>/', views.order_detail, name='order_detail'),
    path('order/<int:order_id>/qr-pay/', views.qr_payment, name='qr_payment'),
    path('api/orders/<int:order_id>/status/', views.order_status_api, name='order_status_api'),
    path('api/orders/<int:order_id>/generate-qr/', views.generate_qr_api, name='generate_qr_api'),
    path('api/orders/<int:order_id>/notify-payment/', views.notify_payment_api, name='notify_payment_api'),
    path('api/orders/<int:order_id>/change-payment/', views.change_payment_method_api, name='change_payment_method_api'),
    path('search/', views.search, name='search'),
    path('add-review/<int:product_id>/', views.add_review, name='add_review'),
]
