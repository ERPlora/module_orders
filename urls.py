"""Orders Module URL Configuration"""

from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    # Main
    path('', views.index, name='index'),
    path('active/', views.active_orders, name='active_orders'),

    # Order CRUD
    path('create/', views.order_create, name='create'),
    path('<uuid:order_id>/', views.order_detail, name='detail'),
    path('<uuid:order_id>/edit/', views.order_edit, name='edit'),
    path('<uuid:order_id>/delete/', views.order_delete, name='delete'),

    # Order items
    path('<uuid:order_id>/add-item/', views.add_item, name='add_item'),
    path('<uuid:order_id>/items/<uuid:item_id>/update/', views.update_item_quantity, name='update_item_quantity'),
    path('<uuid:order_id>/items/<uuid:item_id>/remove/', views.remove_item, name='remove_item'),
    path('<uuid:order_id>/items/<uuid:item_id>/ready/', views.mark_item_ready, name='mark_item_ready'),

    # Order workflow
    path('<uuid:order_id>/fire/', views.fire_order, name='fire'),
    path('<uuid:order_id>/bump/', views.bump_order, name='bump'),
    path('<uuid:order_id>/recall/', views.recall_order, name='recall'),
    path('<uuid:order_id>/serve/', views.serve_order, name='serve'),
    path('<uuid:order_id>/cancel/', views.cancel_order, name='cancel'),
    path('<uuid:order_id>/update-status/', views.update_status, name='update_status'),

    # Kitchen Display System
    path('kds/', views.kitchen_display, name='kds'),
    path('kds/<uuid:station_id>/', views.kitchen_display, name='kds_station'),

    # Kitchen Stations
    path('stations/', views.stations_list, name='stations'),
    path('stations/add/', views.station_add, name='station_add'),
    path('stations/<uuid:station_id>/edit/', views.station_edit, name='station_edit'),
    path('stations/<uuid:station_id>/delete/', views.station_delete, name='station_delete'),

    # Routing
    path('routing/', views.routing, name='routing'),
    path('routing/product/assign/', views.assign_product_station, name='assign_product_station'),
    path('routing/category/assign/', views.assign_category_station, name='assign_category_station'),
    path('routing/product/<uuid:product_id>/remove/', views.remove_product_routing, name='remove_product_routing'),
    path('routing/category/<uuid:category_id>/remove/', views.remove_category_routing, name='remove_category_routing'),

    # History
    path('history/', views.history, name='history'),

    # API (JSON)
    path('api/orders/create/', views.api_create_order, name='api_create_order'),
    path('api/orders/<uuid:order_id>/', views.api_get_order, name='api_get_order'),
    path('api/orders/pending/', views.api_pending_orders, name='api_pending_orders'),
    path('api/orders/table/<uuid:table_id>/', views.api_orders_by_table, name='api_orders_by_table'),
    path('api/orders/stats/', views.api_order_stats, name='api_order_stats'),

    # Item API
    path('api/items/<uuid:item_id>/bump/', views.bump_item, name='api_bump_item'),
    path('api/items/<uuid:item_id>/cancel/', views.cancel_item, name='api_cancel_item'),
    path('api/items/<uuid:item_id>/quantity/', views.modify_item_quantity, name='api_modify_quantity'),

    # Station API
    path('api/stations/summary/', views.api_station_summary, name='api_station_summary'),
    path('api/stations/<uuid:station_id>/items/', views.api_station_items, name='api_station_items'),

    # Settings
    path('settings/', views.settings, name='settings'),
    path('settings/save/', views.settings_save, name='settings_save'),
    path('settings/toggle/', views.settings_toggle, name='settings_toggle'),
    path('settings/input/', views.settings_input, name='settings_input'),
    path('settings/reset/', views.settings_reset, name='settings_reset'),
]
