from django.contrib import admin
from .models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('code', 'customer_name', 'order_type', 'payment_method', 'is_paid', 'status', 'created_at')
    list_filter = ('status', 'order_type', 'payment_method', 'is_paid')
    search_fields = ('code', 'customer_name', 'customer_contact')
    inlines = [OrderItemInline]
