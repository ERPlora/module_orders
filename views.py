"""
Orders Module Views

Handles HTTP requests for order management and kitchen display.
"""

import json
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods, require_POST, require_GET
from django.utils import timezone

from apps.accounts.decorators import login_required

from .models import (
    OrdersConfig,
    KitchenStation,
    Order,
    OrderItem,
    ProductStation,
    CategoryStation
)
from .services import OrderService


# ==============================================================================
# PAGE VIEWS
# ==============================================================================

@login_required
def index(request):
    """Main orders page - pending orders list."""
    orders = OrderService.get_pending_orders()
    stations = KitchenStation.objects.filter(is_active=True)

    return render(request, 'orders/index.html', {
        'orders': orders,
        'stations': stations,
        'page_title': 'Orders',
        'page_type': 'list',
    })


@login_required
def kitchen_display(request, station_id=None):
    """Kitchen display system (KDS) view."""
    stations = KitchenStation.objects.filter(is_active=True)

    if station_id:
        station = get_object_or_404(KitchenStation, pk=station_id)
        items = OrderService.get_orders_by_station(station_id)
    else:
        station = None
        items = []

    return render(request, 'orders/kds.html', {
        'stations': stations,
        'current_station': station,
        'items': items,
        'page_title': 'Kitchen Display',
        'page_type': 'list',
    })


@login_required
def order_detail(request, order_id):
    """Order detail view."""
    order = get_object_or_404(Order, pk=order_id)
    items = order.items.select_related('station').order_by('created_at')

    return render(request, 'orders/order_detail.html', {
        'order': order,
        'items': items,
        'page_title': f'Order #{order.order_number}',
        'page_type': 'detail',
        'back_url': '/modules/orders/',
    })


@login_required
def order_create(request):
    """Create new order page."""
    stations = KitchenStation.objects.filter(is_active=True)

    return render(request, 'orders/order_form.html', {
        'stations': stations,
        'page_title': 'New Order',
        'page_type': 'form',
        'back_url': '/modules/orders/',
    })


@login_required
def stations_list(request):
    """List kitchen stations."""
    stations = KitchenStation.objects.all().order_by('order', 'name')

    return render(request, 'orders/stations.html', {
        'stations': stations,
        'page_title': 'Kitchen Stations',
        'page_type': 'list',
    })


@login_required
def station_create(request):
    """Create new kitchen station."""
    return render(request, 'orders/station_form.html', {
        'page_title': 'New Station',
        'page_type': 'form',
        'back_url': '/modules/orders/stations/',
    })


@login_required
def station_edit(request, station_id):
    """Edit kitchen station."""
    station = get_object_or_404(KitchenStation, pk=station_id)

    return render(request, 'orders/station_form.html', {
        'station': station,
        'page_title': f'Edit {station.name}',
        'page_type': 'form',
        'back_url': '/modules/orders/stations/',
    })


@login_required
def routing(request):
    """Product/category routing configuration."""
    stations = KitchenStation.objects.filter(is_active=True)
    product_mappings = ProductStation.objects.select_related('station').order_by('product_id')
    category_mappings = CategoryStation.objects.select_related('station').order_by('category_id')

    return render(request, 'orders/routing.html', {
        'stations': stations,
        'product_mappings': product_mappings,
        'category_mappings': category_mappings,
        'page_title': 'Order Routing',
        'page_type': 'list',
    })


@login_required
def orders_settings(request):
    """Settings page."""
    config = OrdersConfig.get_config()

    return render(request, 'orders/settings.html', {
        'config': config,
        'page_title': 'Orders Settings',
        'page_type': 'list',
    })


# ==============================================================================
# ORDER API
# ==============================================================================

@login_required
@require_POST
def api_create_order(request):
    """Create a new order."""
    try:
        data = json.loads(request.body)

        items = data.get('items', [])
        if not items:
            return JsonResponse({'error': 'At least one item is required'}, status=400)

        order = OrderService.create_order(
            table_id=data.get('table_id'),
            sale_id=data.get('sale_id'),
            items=items,
            created_by=data.get('created_by', ''),
            round_number=data.get('round_number', 1),
            notes=data.get('notes', ''),
            auto_route=data.get('auto_route', True)
        )

        return JsonResponse({
            'success': True,
            'order_id': order.id,
            'order_number': order.order_number,
            'item_count': order.item_count
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def api_add_item(request, order_id):
    """Add item to existing order."""
    try:
        order = get_object_or_404(Order, pk=order_id)
        data = json.loads(request.body)

        product_id = data.get('product_id')
        product_name = data.get('product_name', f'Product {product_id}')

        if not product_id:
            return JsonResponse({'error': 'product_id is required'}, status=400)

        item = OrderService.add_item_to_order(
            order=order,
            product_id=product_id,
            product_name=product_name,
            quantity=data.get('quantity', 1),
            modifiers=data.get('modifiers', ''),
            notes=data.get('notes', ''),
            seat_number=data.get('seat_number')
        )

        return JsonResponse({
            'success': True,
            'item_id': item.id,
            'message': f'Added {item.quantity}x {item.product_name}'
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)


@login_required
@require_POST
def api_fire_order(request, order_id):
    """Fire order to kitchen."""
    try:
        order = OrderService.fire_order(order_id)

        return JsonResponse({
            'success': True,
            'status': order.status,
            'fired_at': order.fired_at.isoformat() if order.fired_at else None
        })

    except Order.DoesNotExist:
        return JsonResponse({'error': 'Order not found'}, status=404)


@login_required
@require_POST
def api_bump_item(request, item_id):
    """Bump (mark ready) a single item."""
    try:
        item = OrderService.bump_item(item_id)

        return JsonResponse({
            'success': True,
            'item_status': item.status,
            'order_status': item.order.status
        })

    except OrderItem.DoesNotExist:
        return JsonResponse({'error': 'Item not found'}, status=404)


@login_required
@require_POST
def api_bump_order(request, order_id):
    """Bump (mark ready) entire order."""
    try:
        order = OrderService.bump_order(order_id)

        return JsonResponse({
            'success': True,
            'status': order.status,
            'ready_at': order.ready_at.isoformat() if order.ready_at else None
        })

    except Order.DoesNotExist:
        return JsonResponse({'error': 'Order not found'}, status=404)


@login_required
@require_POST
def api_recall_order(request, order_id):
    """Recall a ready order back to preparing."""
    try:
        order = OrderService.recall_order(order_id)

        return JsonResponse({
            'success': True,
            'status': order.status
        })

    except Order.DoesNotExist:
        return JsonResponse({'error': 'Order not found'}, status=404)


@login_required
@require_POST
def api_serve_order(request, order_id):
    """Mark order as served."""
    try:
        order = Order.objects.get(pk=order_id)
        order.mark_served()

        return JsonResponse({
            'success': True,
            'status': order.status,
            'served_at': order.served_at.isoformat() if order.served_at else None
        })

    except Order.DoesNotExist:
        return JsonResponse({'error': 'Order not found'}, status=404)


@login_required
@require_POST
def api_cancel_order(request, order_id):
    """Cancel an order."""
    try:
        reason = request.POST.get('reason', '')
        order = OrderService.cancel_order(order_id, reason)

        return JsonResponse({
            'success': True,
            'status': order.status
        })

    except Order.DoesNotExist:
        return JsonResponse({'error': 'Order not found'}, status=404)


@login_required
@require_POST
def api_cancel_item(request, item_id):
    """Cancel a single item."""
    try:
        item = OrderService.cancel_item(item_id)

        return JsonResponse({
            'success': True,
            'status': item.status
        })

    except OrderItem.DoesNotExist:
        return JsonResponse({'error': 'Item not found'}, status=404)


@login_required
@require_POST
def api_modify_item_quantity(request, item_id):
    """Modify item quantity."""
    try:
        data = json.loads(request.body)
        quantity = data.get('quantity', 1)

        item = OrderService.modify_item_quantity(item_id, quantity)

        return JsonResponse({
            'success': True,
            'quantity': item.quantity
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except OrderItem.DoesNotExist:
        return JsonResponse({'error': 'Item not found'}, status=404)


@login_required
@require_GET
def api_get_order(request, order_id):
    """Get order details."""
    order = get_object_or_404(Order, pk=order_id)

    return JsonResponse({
        'success': True,
        'order': {
            'id': order.id,
            'order_number': order.order_number,
            'table': order.table_display,
            'status': order.status,
            'priority': order.priority,
            'round_number': order.round_number,
            'created_by': order.created_by,
            'notes': order.notes,
            'elapsed_minutes': order.elapsed_minutes,
            'is_delayed': order.is_delayed,
            'items': [
                {
                    'id': item.id,
                    'product_name': item.product_name,
                    'quantity': item.quantity,
                    'modifiers': item.modifiers,
                    'notes': item.notes,
                    'status': item.status,
                    'station': item.station.name if item.station else None
                }
                for item in order.items.all()
            ]
        }
    })


@login_required
@require_GET
def api_pending_orders(request):
    """Get all pending orders."""
    orders = OrderService.get_pending_orders()

    return JsonResponse({
        'success': True,
        'orders': [
            {
                'id': o.id,
                'order_number': o.order_number,
                'table': o.table_display,
                'status': o.status,
                'priority': o.priority,
                'item_count': o.item_count,
                'elapsed_minutes': o.elapsed_minutes,
                'is_delayed': o.is_delayed
            }
            for o in orders
        ]
    })


@login_required
@require_GET
def api_orders_by_table(request, table_id):
    """Get orders for a table."""
    orders = OrderService.get_orders_by_table(table_id)

    return JsonResponse({
        'success': True,
        'orders': [
            {
                'id': o.id,
                'order_number': o.order_number,
                'status': o.status,
                'round_number': o.round_number,
                'item_count': o.item_count
            }
            for o in orders
        ]
    })


@login_required
@require_GET
def api_station_items(request, station_id):
    """Get pending items for a station."""
    items = OrderService.get_orders_by_station(station_id)

    return JsonResponse({
        'success': True,
        'items': items
    })


@login_required
@require_GET
def api_station_summary(request):
    """Get summary of pending items per station."""
    summary = OrderService.get_station_summary()

    return JsonResponse({
        'success': True,
        'stations': summary
    })


@login_required
@require_GET
def api_order_stats(request):
    """Get order statistics."""
    date_str = request.GET.get('date')
    date = None

    if date_str:
        from datetime import datetime
        date = datetime.strptime(date_str, '%Y-%m-%d').date()

    stats = OrderService.get_order_stats(date)

    return JsonResponse({
        'success': True,
        **stats
    })


# ==============================================================================
# STATION API
# ==============================================================================

@login_required
@require_POST
def api_create_station(request):
    """Create a new kitchen station."""
    try:
        data = json.loads(request.body)

        name = data.get('name', '').strip()
        if not name:
            return JsonResponse({'error': 'Name is required'}, status=400)

        if KitchenStation.objects.filter(name__iexact=name).exists():
            return JsonResponse({'error': 'Station with this name already exists'}, status=400)

        station = KitchenStation.objects.create(
            name=name,
            name_es=data.get('name_es', ''),
            description=data.get('description', ''),
            color=data.get('color', '#F97316'),
            icon=data.get('icon', 'flame-outline'),
            printer_name=data.get('printer_name', ''),
            order=data.get('order', 0)
        )

        return JsonResponse({
            'success': True,
            'station_id': station.id,
            'message': f'Station "{station.name}" created'
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)


@login_required
@require_POST
def api_update_station(request, station_id):
    """Update a kitchen station."""
    try:
        station = get_object_or_404(KitchenStation, pk=station_id)
        data = json.loads(request.body)

        name = data.get('name', '').strip()
        if name and name != station.name:
            if KitchenStation.objects.filter(name__iexact=name).exclude(pk=station_id).exists():
                return JsonResponse({'error': 'Station with this name already exists'}, status=400)
            station.name = name

        if 'name_es' in data:
            station.name_es = data['name_es']
        if 'description' in data:
            station.description = data['description']
        if 'color' in data:
            station.color = data['color']
        if 'icon' in data:
            station.icon = data['icon']
        if 'printer_name' in data:
            station.printer_name = data['printer_name']
        if 'order' in data:
            station.order = data['order']
        if 'is_active' in data:
            station.is_active = data['is_active']

        station.save()

        return JsonResponse({
            'success': True,
            'message': f'Station "{station.name}" updated'
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)


@login_required
@require_POST
def api_delete_station(request, station_id):
    """Delete a kitchen station (soft delete)."""
    station = get_object_or_404(KitchenStation, pk=station_id)
    station_name = station.name
    station.is_active = False
    station.save()

    return JsonResponse({
        'success': True,
        'message': f'Station "{station_name}" deleted'
    })


@login_required
@require_GET
def api_list_stations(request):
    """List all kitchen stations."""
    stations = KitchenStation.objects.filter(is_active=True).order_by('order', 'name')

    return JsonResponse({
        'success': True,
        'stations': [
            {
                'id': s.id,
                'name': s.name,
                'name_es': s.name_es,
                'color': s.color,
                'icon': s.icon,
                'pending_count': s.pending_count
            }
            for s in stations
        ]
    })


# ==============================================================================
# ROUTING API
# ==============================================================================

@login_required
@require_POST
def api_assign_product_station(request):
    """Assign a product to a station."""
    try:
        data = json.loads(request.body)

        product_id = data.get('product_id')
        station_id = data.get('station_id')

        if not product_id or not station_id:
            return JsonResponse({'error': 'product_id and station_id are required'}, status=400)

        mapping = OrderService.assign_product_to_station(product_id, station_id)

        return JsonResponse({
            'success': True,
            'mapping_id': mapping.id
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except KitchenStation.DoesNotExist:
        return JsonResponse({'error': 'Station not found'}, status=404)


@login_required
@require_POST
def api_assign_category_station(request):
    """Assign a category to a station."""
    try:
        data = json.loads(request.body)

        category_id = data.get('category_id')
        station_id = data.get('station_id')

        if not category_id or not station_id:
            return JsonResponse({'error': 'category_id and station_id are required'}, status=400)

        mapping = OrderService.assign_category_to_station(category_id, station_id)

        return JsonResponse({
            'success': True,
            'mapping_id': mapping.id
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except KitchenStation.DoesNotExist:
        return JsonResponse({'error': 'Station not found'}, status=404)


@login_required
@require_POST
def api_remove_product_routing(request, product_id):
    """Remove product routing."""
    deleted, _ = ProductStation.objects.filter(product_id=product_id).delete()

    return JsonResponse({
        'success': True,
        'deleted': deleted > 0
    })


@login_required
@require_POST
def api_remove_category_routing(request, category_id):
    """Remove category routing."""
    deleted, _ = CategoryStation.objects.filter(category_id=category_id).delete()

    return JsonResponse({
        'success': True,
        'deleted': deleted > 0
    })


# ==============================================================================
# SETTINGS API
# ==============================================================================

@login_required
@require_POST
def settings_save(request):
    """Save orders settings."""
    try:
        data = json.loads(request.body)
        config = OrdersConfig.get_config()

        fields = [
            'auto_print_tickets', 'show_prep_time', 'alert_threshold_minutes',
            'use_rounds', 'auto_fire_on_round', 'sound_on_new_order'
        ]

        for field in fields:
            if field in data:
                setattr(config, field, data[field])

        config.save()

        return JsonResponse({'success': True})

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)


@login_required
@require_POST
def settings_toggle(request):
    """Toggle a boolean setting."""
    config = OrdersConfig.get_config()
    name = request.POST.get('name')
    value = request.POST.get('value') == 'true'

    if hasattr(config, name):
        setattr(config, name, value)
        config.save()

    return HttpResponse(status=204)


@login_required
@require_POST
def settings_input(request):
    """Update a numeric setting."""
    config = OrdersConfig.get_config()
    name = request.POST.get('name')
    value = request.POST.get('value')

    if hasattr(config, name):
        setattr(config, name, int(value))
        config.save()

    return HttpResponse(status=204)


@login_required
@require_POST
def settings_reset(request):
    """Reset settings to defaults."""
    config = OrdersConfig.get_config()
    config.auto_print_tickets = True
    config.show_prep_time = True
    config.alert_threshold_minutes = 15
    config.use_rounds = True
    config.auto_fire_on_round = False
    config.sound_on_new_order = True
    config.save()

    return HttpResponse(status=204)
