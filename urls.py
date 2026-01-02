"""
Orders Module URLs
"""

from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    # Page views
    path('', views.index, name='index'),
    path('kds/', views.kitchen_display, name='kds'),
    path('kds/<int:station_id>/', views.kitchen_display, name='kds_station'),
    path('stations/', views.stations_list, name='stations'),
    path('stations/new/', views.station_create, name='station_create'),
    path('stations/<int:station_id>/edit/', views.station_edit, name='station_edit'),
    path('routing/', views.routing, name='routing'),
    path('settings/', views.orders_settings, name='settings'),

    # Order pages
    path('orders/new/', views.order_create, name='order_create'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),

    # Order API
    path('api/orders/create/', views.api_create_order, name='api_create_order'),
    path('api/orders/<int:order_id>/', views.api_get_order, name='api_get_order'),
    path('api/orders/<int:order_id>/add-item/', views.api_add_item, name='api_add_item'),
    path('api/orders/<int:order_id>/fire/', views.api_fire_order, name='api_fire_order'),
    path('api/orders/<int:order_id>/bump/', views.api_bump_order, name='api_bump_order'),
    path('api/orders/<int:order_id>/recall/', views.api_recall_order, name='api_recall_order'),
    path('api/orders/<int:order_id>/serve/', views.api_serve_order, name='api_serve_order'),
    path('api/orders/<int:order_id>/cancel/', views.api_cancel_order, name='api_cancel_order'),
    path('api/orders/pending/', views.api_pending_orders, name='api_pending_orders'),
    path('api/orders/table/<int:table_id>/', views.api_orders_by_table, name='api_orders_by_table'),
    path('api/orders/stats/', views.api_order_stats, name='api_order_stats'),

    # Item API
    path('api/items/<int:item_id>/bump/', views.api_bump_item, name='api_bump_item'),
    path('api/items/<int:item_id>/cancel/', views.api_cancel_item, name='api_cancel_item'),
    path('api/items/<int:item_id>/quantity/', views.api_modify_item_quantity, name='api_modify_quantity'),

    # Station API
    path('api/stations/', views.api_list_stations, name='api_list_stations'),
    path('api/stations/create/', views.api_create_station, name='api_create_station'),
    path('api/stations/<int:station_id>/update/', views.api_update_station, name='api_update_station'),
    path('api/stations/<int:station_id>/delete/', views.api_delete_station, name='api_delete_station'),
    path('api/stations/<int:station_id>/items/', views.api_station_items, name='api_station_items'),
    path('api/stations/summary/', views.api_station_summary, name='api_station_summary'),

    # Routing API
    path('api/routing/product/', views.api_assign_product_station, name='api_assign_product'),
    path('api/routing/category/', views.api_assign_category_station, name='api_assign_category'),
    path('api/routing/product/<int:product_id>/remove/', views.api_remove_product_routing, name='api_remove_product_routing'),
    path('api/routing/category/<int:category_id>/remove/', views.api_remove_category_routing, name='api_remove_category_routing'),

    # Settings API
    path('settings/save/', views.settings_save, name='settings_save'),
    path('settings/toggle/', views.settings_toggle, name='settings_toggle'),
    path('settings/input/', views.settings_input, name='settings_input'),
    path('settings/reset/', views.settings_reset, name='settings_reset'),
]
