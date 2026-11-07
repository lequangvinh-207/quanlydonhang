from django.urls import path
from . import customer_views

app_name = 'customer_orders'

urlpatterns = [
    path('gio-hang/', customer_views.cart_view, name='cart'),
    path('gio-hang/them/<int:product_id>/', customer_views.cart_add, name='cart_add'),
    path('gio-hang/cap-nhat/<int:product_id>/', customer_views.cart_update, name='cart_update'),
    path('gio-hang/xoa/<int:product_id>/', customer_views.cart_remove, name='cart_remove'),
    path('dat-hang/', customer_views.checkout, name='checkout'),
    path('tra-cuu/', customer_views.order_lookup, name='lookup'),
    path('dat-hang/thanh-cong/<str:code>/', customer_views.order_success, name='order_success'),
]
