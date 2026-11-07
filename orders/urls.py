from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('', views.order_list, name='order_list'),
    path('create/', views.order_create, name='order_create'),
    path('<int:pk>/', views.order_detail, name='order_detail'),
    path('<int:pk>/invoice/', views.order_invoice, name='order_invoice'),
    path('<int:pk>/phieu-in/', views.order_print_slip, name='order_print_slip'),
    path('<int:pk>/da-thu-tien/', views.order_mark_paid, name='order_mark_paid'),
    path('<int:pk>/edit/', views.order_update, name='order_update'),
    path('<int:pk>/change-status/', views.order_change_status, name='order_change_status'),
    path('<int:pk>/cancel/', views.order_cancel, name='order_cancel'),
]
