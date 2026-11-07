from django.contrib import admin
from .models import Product

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'cost_price', 'is_available', 'is_combo', 'created_at')
    list_filter = ('is_available', 'is_combo')
    search_fields = ('name', 'description')
    list_editable = ('price', 'is_available')
