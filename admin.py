from django.contrib import admin
from .models import (
    OrdersSettings,
    KitchenStation,
    Order,
    OrderItem,
    ProductStation,
    CategoryStation
)


@admin.register(OrdersSettings)
class OrdersSettingsAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'use_rounds', 'auto_print_tickets', 'alert_threshold_minutes']


@admin.register(KitchenStation)
class KitchenStationAdmin(admin.ModelAdmin):
    list_display = ['name', 'color', 'printer_name', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name']


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['created_at', 'started_at', 'completed_at']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'table_id', 'status', 'priority', 'round_number', 'created_at']
    list_filter = ['status', 'priority', 'created_at']
    search_fields = ['order_number']
    inlines = [OrderItemInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'product_name', 'quantity', 'station', 'status']
    list_filter = ['status', 'station']
    search_fields = ['product_name', 'order__order_number']


@admin.register(ProductStation)
class ProductStationAdmin(admin.ModelAdmin):
    list_display = ['product_id', 'station']
    list_filter = ['station']


@admin.register(CategoryStation)
class CategoryStationAdmin(admin.ModelAdmin):
    list_display = ['category_id', 'station']
    list_filter = ['station']
