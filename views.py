"""
Orders Module Views

Order management, kitchen display, station routing, and settings.
"""

import json
from decimal import Decimal

from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST, require_GET
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db import transaction
from django.db.models import Q, Sum, Count, F, ExpressionWrapper, DurationField

from apps.core.htmx import htmx_view
from apps.accounts.decorators import login_required, permission_required
from apps.modules_runtime.navigation import with_module_nav

from .models import (
    OrdersSettings, KitchenStation, Order, OrderItem, OrderModifier,
    ProductStation, CategoryStation, get_station_for_product,
)
from .forms import OrderForm, OrderItemForm, KitchenStationForm


def _hub_id(request):
    return request.session.get('hub_id')


def _employee(request):
    from apps.accounts.models import LocalUser
    user_id = request.session.get('local_user_id')
    return LocalUser.objects.filter(id=user_id).first() if user_id else None


# =============================================================================
# Active Orders (Index)
# =============================================================================

@login_required
@with_module_nav('orders', 'dashboard')
@htmx_view('orders/pages/index.html', 'orders/partials/active_orders.html')
def index(request):
    return active_orders(request)


@login_required
@with_module_nav('orders', 'active')
@htmx_view('orders/pages/active_orders.html', 'orders/partials/active_orders.html')
def active_orders(request):
    hub = _hub_id(request)
    status_filter = request.GET.get('status', '')
    order_type_filter = request.GET.get('order_type', '')

    orders_qs = Order.objects.filter(
        hub_id=hub, is_deleted=False,
        status__in=['pending', 'preparing', 'ready', 'served'],
    ).select_related('table', 'waiter', 'customer').prefetch_related('items').order_by('-created_at')

    if status_filter:
        orders_qs = orders_qs.filter(status=status_filter)
    if order_type_filter:
        orders_qs = orders_qs.filter(order_type=order_type_filter)

    status_counts = Order.objects.filter(
        hub_id=hub, is_deleted=False,
        status__in=['pending', 'preparing', 'ready', 'served'],
    ).values('status').annotate(count=Count('id'))
    counts = {item['status']: item['count'] for item in status_counts}

    return {
        'orders': orders_qs,
        'status_filter': status_filter,
        'order_type_filter': order_type_filter,
        'status_choices': [c for c in Order.STATUS_CHOICES if c[0] in ['pending', 'preparing', 'ready', 'served']],
        'order_type_choices': Order.ORDER_TYPE_CHOICES,
        'pending_count': counts.get('pending', 0),
        'preparing_count': counts.get('preparing', 0),
        'ready_count': counts.get('ready', 0),
        'served_count': counts.get('served', 0),
    }


# =============================================================================
# Order CRUD
# =============================================================================

@login_required
@with_module_nav('orders', 'active')
@htmx_view('orders/pages/order_detail.html', 'orders/partials/order_detail.html')
def order_detail(request, order_id):
    hub = _hub_id(request)
    order = get_object_or_404(Order, pk=order_id, hub_id=hub, is_deleted=False)
    items = order.items.filter(is_deleted=False).select_related('product', 'station')

    return {
        'order': order,
        'items': items,
    }


@login_required
@with_module_nav('orders', 'active')
@htmx_view('orders/pages/order_form.html', 'orders/partials/order_form.html')
def order_create(request):
    hub = _hub_id(request)
    waiter = _employee(request)

    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.hub_id = hub
            order.order_number = Order.generate_order_number(hub)
            order.waiter = waiter
            order.save()
            return {
                'orders': Order.objects.filter(
                    hub_id=hub, is_deleted=False,
                    status__in=['pending', 'preparing', 'ready', 'served'],
                ).order_by('-created_at'),
                'template': 'orders/partials/active_orders.html',
            }
    else:
        form = OrderForm()

    return {'form': form, 'is_new': True}


@login_required
@with_module_nav('orders', 'active')
@htmx_view('orders/pages/order_form.html', 'orders/partials/order_form.html')
def order_edit(request, order_id):
    hub = _hub_id(request)
    order = get_object_or_404(Order, pk=order_id, hub_id=hub, is_deleted=False)

    if request.method == 'POST':
        form = OrderForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
            return {
                'order': order,
                'items': order.items.filter(is_deleted=False),
                'template': 'orders/partials/order_detail.html',
            }
    else:
        form = OrderForm(instance=order)

    return {'form': form, 'order': order, 'is_new': False}


@login_required
@require_POST
def order_delete(request, order_id):
    hub = _hub_id(request)
    order = get_object_or_404(Order, pk=order_id, hub_id=hub, is_deleted=False)
    order.is_deleted = True
    order.deleted_at = timezone.now()
    order.save(update_fields=['is_deleted', 'deleted_at', 'updated_at'])
    return JsonResponse({'success': True, 'message': str(_('Order deleted'))})


# =============================================================================
# Order Items
# =============================================================================

@login_required
@with_module_nav('orders', 'active')
@htmx_view('orders/pages/add_item.html', 'orders/partials/add_item_form.html')
def add_item(request, order_id):
    hub = _hub_id(request)
    order = get_object_or_404(Order, pk=order_id, hub_id=hub, is_deleted=False)

    if request.method == 'POST':
        form = OrderItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.hub_id = hub
            item.order = order

            # Auto-route to station
            if item.product_id:
                station = get_station_for_product(hub, item.product_id)
                if station:
                    item.station = station

            item.save()
            order.calculate_totals()
            order.save(update_fields=['subtotal', 'total', 'updated_at'])

            return {
                'order': order,
                'items': order.items.filter(is_deleted=False),
                'template': 'orders/partials/order_detail.html',
            }
    else:
        form = OrderItemForm()

    return {'form': form, 'order': order}


@login_required
@require_POST
def update_item_quantity(request, order_id, item_id):
    hub = _hub_id(request)
    order = get_object_or_404(Order, pk=order_id, hub_id=hub, is_deleted=False)
    item = get_object_or_404(OrderItem, pk=item_id, order=order, is_deleted=False)

    quantity = request.POST.get('quantity')
    if quantity:
        item.quantity = max(1, int(quantity))
        item.save()
        order.calculate_totals()
        order.save(update_fields=['subtotal', 'total', 'updated_at'])

    return JsonResponse({
        'success': True,
        'message': str(_('Item updated')),
        'item_total': str(item.total),
        'order_total': str(order.total),
    })


@login_required
@require_POST
def remove_item(request, order_id, item_id):
    hub = _hub_id(request)
    order = get_object_or_404(Order, pk=order_id, hub_id=hub, is_deleted=False)
    item = get_object_or_404(OrderItem, pk=item_id, order=order, is_deleted=False)

    item.is_deleted = True
    item.deleted_at = timezone.now()
    item.save(update_fields=['is_deleted', 'deleted_at', 'updated_at'])

    order.calculate_totals()
    order.save(update_fields=['subtotal', 'total', 'updated_at'])

    return JsonResponse({
        'success': True,
        'message': str(_('Item removed')),
        'order_total': str(order.total),
    })


# =============================================================================
# Order Workflow Actions
# =============================================================================

@login_required
@require_POST
def fire_order(request, order_id):
    hub = _hub_id(request)
    order = get_object_or_404(Order, pk=order_id, hub_id=hub, is_deleted=False)
    order.fire()
    return JsonResponse({
        'success': True,
        'status': order.status,
        'fired_at': order.fired_at.isoformat() if order.fired_at else None,
    })


@login_required
@require_POST
def bump_order(request, order_id):
    hub = _hub_id(request)
    order = get_object_or_404(Order, pk=order_id, hub_id=hub, is_deleted=False)

    order.items.filter(
        is_deleted=False, status__in=['pending', 'preparing'],
    ).update(status='ready', completed_at=timezone.now())
    order.mark_ready()

    return JsonResponse({
        'success': True,
        'status': order.status,
        'ready_at': order.ready_at.isoformat() if order.ready_at else None,
    })


@login_required
@require_POST
def recall_order(request, order_id):
    hub = _hub_id(request)
    order = get_object_or_404(Order, pk=order_id, hub_id=hub, is_deleted=False)
    order.recall()
    return JsonResponse({'success': True, 'status': order.status})


@login_required
@require_POST
def serve_order(request, order_id):
    hub = _hub_id(request)
    order = get_object_or_404(Order, pk=order_id, hub_id=hub, is_deleted=False)
    order.mark_served()
    return JsonResponse({
        'success': True,
        'status': order.status,
        'served_at': order.served_at.isoformat() if order.served_at else None,
    })


@login_required
@require_POST
def cancel_order(request, order_id):
    hub = _hub_id(request)
    order = get_object_or_404(Order, pk=order_id, hub_id=hub, is_deleted=False)

    if order.status in ['paid', 'cancelled']:
        return JsonResponse({'success': False, 'message': str(_('Cannot cancel'))}, status=400)

    reason = request.POST.get('reason', '')
    order.cancel(reason)
    return JsonResponse({'success': True, 'status': order.status})


@login_required
@require_POST
def update_status(request, order_id):
    hub = _hub_id(request)
    order = get_object_or_404(Order, pk=order_id, hub_id=hub, is_deleted=False)
    new_status = request.POST.get('status')
    if new_status and new_status in dict(Order.STATUS_CHOICES):
        order.status = new_status
        order.save(update_fields=['status', 'updated_at'])
        return JsonResponse({'success': True, 'status': new_status})
    return JsonResponse({'success': False, 'message': str(_('Invalid status'))}, status=400)


# =============================================================================
# Item Actions
# =============================================================================

@login_required
@require_POST
def bump_item(request, item_id):
    hub = _hub_id(request)
    item = get_object_or_404(OrderItem, pk=item_id, hub_id=hub, is_deleted=False)
    item.mark_ready()
    return JsonResponse({
        'success': True,
        'item_status': item.status,
        'order_status': item.order.status,
    })


@login_required
@require_POST
def cancel_item(request, item_id):
    hub = _hub_id(request)
    item = get_object_or_404(OrderItem, pk=item_id, hub_id=hub, is_deleted=False)
    item.cancel()
    return JsonResponse({'success': True, 'status': item.status})


@login_required
@require_POST
def modify_item_quantity(request, item_id):
    hub = _hub_id(request)
    item = get_object_or_404(OrderItem, pk=item_id, hub_id=hub, is_deleted=False)

    try:
        data = json.loads(request.body)
        quantity = max(1, int(data.get('quantity', 1)))
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': _('Invalid data')}, status=400)

    item.quantity = quantity
    item.save()
    return JsonResponse({'success': True, 'quantity': item.quantity})


@login_required
@require_POST
def mark_item_ready(request, order_id, item_id):
    hub = _hub_id(request)
    order = get_object_or_404(Order, pk=order_id, hub_id=hub, is_deleted=False)
    item = get_object_or_404(OrderItem, pk=item_id, order=order, is_deleted=False)
    item.mark_ready()

    all_ready = not order.items.filter(
        is_deleted=False, fired_at__isnull=False,
    ).exclude(status__in=['ready', 'served', 'cancelled']).exists()

    return JsonResponse({
        'success': True,
        'message': str(_('Item ready')),
        'order_ready': all_ready,
    })


# =============================================================================
# Kitchen Display System (KDS)
# =============================================================================

@login_required
@with_module_nav('orders', 'active')
@htmx_view('orders/pages/kds.html', 'orders/partials/kds.html')
def kitchen_display(request, station_id=None):
    hub = _hub_id(request)
    stations = KitchenStation.objects.filter(
        hub_id=hub, is_active=True, is_deleted=False,
    ).order_by('sort_order', 'name')

    station = None
    items = []
    if station_id:
        station = get_object_or_404(KitchenStation, pk=station_id, hub_id=hub, is_deleted=False)
        items_qs = OrderItem.objects.filter(
            hub_id=hub, is_deleted=False,
            station=station,
            status__in=['pending', 'preparing'],
        ).select_related('order').order_by('order__priority', 'created_at')

        items = [{
            'id': str(item.pk),
            'order_number': item.order.order_number,
            'table': item.order.table_display,
            'product_name': item.product_name,
            'quantity': item.quantity,
            'modifiers': item.modifiers,
            'notes': item.notes,
            'status': item.status,
            'priority': item.order.priority,
            'elapsed_minutes': item.order.elapsed_minutes,
            'is_delayed': item.order.is_delayed,
        } for item in items_qs]

    return {
        'stations': stations,
        'current_station': station,
        'items': items,
    }


# =============================================================================
# Kitchen Stations
# =============================================================================

@login_required
@with_module_nav('orders', 'active')
@htmx_view('orders/pages/stations.html', 'orders/partials/stations.html')
def stations_list(request):
    hub = _hub_id(request)
    stations = KitchenStation.objects.filter(
        hub_id=hub, is_deleted=False,
    ).order_by('sort_order', 'name')
    return {'stations': stations}


@login_required
@with_module_nav('orders', 'active')
@htmx_view('orders/pages/station_form.html', 'orders/partials/station_form.html')
def station_add(request):
    hub = _hub_id(request)

    if request.method == 'POST':
        form = KitchenStationForm(request.POST)
        if form.is_valid():
            station = form.save(commit=False)
            station.hub_id = hub
            station.save()
            return {
                'stations': KitchenStation.objects.filter(hub_id=hub, is_deleted=False),
                'template': 'orders/partials/stations.html',
            }
    else:
        form = KitchenStationForm()

    return {'form': form, 'is_new': True}


@login_required
@with_module_nav('orders', 'active')
@htmx_view('orders/pages/station_form.html', 'orders/partials/station_form.html')
def station_edit(request, station_id):
    hub = _hub_id(request)
    station = get_object_or_404(KitchenStation, pk=station_id, hub_id=hub, is_deleted=False)

    if request.method == 'POST':
        form = KitchenStationForm(request.POST, instance=station)
        if form.is_valid():
            form.save()
            return {
                'stations': KitchenStation.objects.filter(hub_id=hub, is_deleted=False),
                'template': 'orders/partials/stations.html',
            }
    else:
        form = KitchenStationForm(instance=station)

    return {'form': form, 'station': station, 'is_new': False}


@login_required
@require_POST
def station_delete(request, station_id):
    hub = _hub_id(request)
    station = get_object_or_404(KitchenStation, pk=station_id, hub_id=hub, is_deleted=False)
    station.is_deleted = True
    station.deleted_at = timezone.now()
    station.save(update_fields=['is_deleted', 'deleted_at', 'updated_at'])
    return JsonResponse({'success': True, 'message': str(_('Station deleted'))})


# =============================================================================
# Routing
# =============================================================================

@login_required
@with_module_nav('orders', 'active')
@htmx_view('orders/pages/routing.html', 'orders/partials/routing.html')
def routing(request):
    hub = _hub_id(request)
    stations = KitchenStation.objects.filter(
        hub_id=hub, is_active=True, is_deleted=False,
    ).order_by('sort_order', 'name')

    product_mappings = ProductStation.objects.filter(
        hub_id=hub, is_deleted=False,
    ).select_related('product', 'station').order_by('product__name')

    category_mappings = CategoryStation.objects.filter(
        hub_id=hub, is_deleted=False,
    ).select_related('category', 'station').order_by('category__name')

    return {
        'stations': stations,
        'product_mappings': product_mappings,
        'category_mappings': category_mappings,
    }


@login_required
@require_POST
def assign_product_station(request):
    hub = _hub_id(request)
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        station_id = data.get('station_id')
        if not product_id or not station_id:
            return JsonResponse({'error': _('product_id and station_id required')}, status=400)

        station = get_object_or_404(KitchenStation, pk=station_id, hub_id=hub, is_deleted=False)
        mapping, _ = ProductStation.objects.update_or_create(
            hub_id=hub, product_id=product_id,
            defaults={'station': station},
        )
        return JsonResponse({'success': True, 'mapping_id': str(mapping.pk)})
    except json.JSONDecodeError:
        return JsonResponse({'error': _('Invalid JSON')}, status=400)


@login_required
@require_POST
def assign_category_station(request):
    hub = _hub_id(request)
    try:
        data = json.loads(request.body)
        category_id = data.get('category_id')
        station_id = data.get('station_id')
        if not category_id or not station_id:
            return JsonResponse({'error': _('category_id and station_id required')}, status=400)

        station = get_object_or_404(KitchenStation, pk=station_id, hub_id=hub, is_deleted=False)
        mapping, _ = CategoryStation.objects.update_or_create(
            hub_id=hub, category_id=category_id,
            defaults={'station': station},
        )
        return JsonResponse({'success': True, 'mapping_id': str(mapping.pk)})
    except json.JSONDecodeError:
        return JsonResponse({'error': _('Invalid JSON')}, status=400)


@login_required
@require_POST
def remove_product_routing(request, product_id):
    hub = _hub_id(request)
    deleted, _ = ProductStation.objects.filter(hub_id=hub, product_id=product_id).delete()
    return JsonResponse({'success': True, 'deleted': deleted > 0})


@login_required
@require_POST
def remove_category_routing(request, category_id):
    hub = _hub_id(request)
    deleted, _ = CategoryStation.objects.filter(hub_id=hub, category_id=category_id).delete()
    return JsonResponse({'success': True, 'deleted': deleted > 0})


# =============================================================================
# History
# =============================================================================

@login_required
@with_module_nav('orders', 'history')
@htmx_view('orders/pages/history.html', 'orders/partials/history.html')
def history(request):
    hub = _hub_id(request)
    search_query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '')
    order_type_filter = request.GET.get('order_type', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    orders_qs = Order.objects.filter(
        hub_id=hub, is_deleted=False,
    ).select_related('waiter', 'customer', 'table').order_by('-created_at')

    if search_query:
        orders_qs = orders_qs.filter(
            Q(order_number__icontains=search_query)
            | Q(waiter__name__icontains=search_query)
            | Q(customer__name__icontains=search_query)
        )
    if status_filter:
        orders_qs = orders_qs.filter(status=status_filter)
    if order_type_filter:
        orders_qs = orders_qs.filter(order_type=order_type_filter)
    if date_from:
        orders_qs = orders_qs.filter(created_at__date__gte=date_from)
    if date_to:
        orders_qs = orders_qs.filter(created_at__date__lte=date_to)

    completed = orders_qs.filter(status='paid')
    total_revenue = completed.aggregate(total=Sum('total'))['total'] or Decimal('0')

    return {
        'orders': orders_qs[:100],
        'search_query': search_query,
        'status_filter': status_filter,
        'order_type_filter': order_type_filter,
        'date_from': date_from,
        'date_to': date_to,
        'total_revenue': total_revenue,
        'orders_count': completed.count(),
        'status_choices': Order.STATUS_CHOICES,
        'order_type_choices': Order.ORDER_TYPE_CHOICES,
    }


# =============================================================================
# API Endpoints (JSON)
# =============================================================================

@login_required
@require_POST
def api_create_order(request):
    """Create order with items via JSON API."""
    hub = _hub_id(request)
    waiter = _employee(request)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': _('Invalid JSON')}, status=400)

    items_data = data.get('items', [])
    if not items_data:
        return JsonResponse({'error': _('At least one item is required')}, status=400)

    with transaction.atomic():
        order = Order.objects.create(
            hub_id=hub,
            order_number=Order.generate_order_number(hub),
            table_id=data.get('table_id'),
            sale_id=data.get('sale_id'),
            order_type=data.get('order_type', 'dine_in'),
            priority=data.get('priority', 'normal'),
            round_number=data.get('round_number', 1),
            notes=data.get('notes', ''),
            waiter=waiter,
        )

        for item_data in items_data:
            product_id = item_data.get('product_id')
            station = None
            if data.get('auto_route', True) and product_id:
                station = get_station_for_product(hub, product_id)

            OrderItem.objects.create(
                hub_id=hub,
                order=order,
                product_id=product_id,
                product_name=item_data.get('product_name', ''),
                unit_price=Decimal(str(item_data.get('unit_price', '0'))),
                quantity=item_data.get('quantity', 1),
                station=station,
                modifiers=item_data.get('modifiers', ''),
                notes=item_data.get('notes', ''),
                seat_number=item_data.get('seat_number'),
            )

        order.calculate_totals()
        order.save(update_fields=['subtotal', 'total', 'updated_at'])

    return JsonResponse({
        'success': True,
        'order_id': str(order.pk),
        'order_number': order.order_number,
        'item_count': order.item_count,
    })


@login_required
@require_GET
def api_get_order(request, order_id):
    hub = _hub_id(request)
    order = get_object_or_404(Order, pk=order_id, hub_id=hub, is_deleted=False)

    return JsonResponse({
        'success': True,
        'order': {
            'id': str(order.pk),
            'order_number': order.order_number,
            'table': order.table_display,
            'status': order.status,
            'priority': order.priority,
            'order_type': order.order_type,
            'round_number': order.round_number,
            'notes': order.notes,
            'subtotal': str(order.subtotal),
            'total': str(order.total),
            'elapsed_minutes': order.elapsed_minutes,
            'is_delayed': order.is_delayed,
            'items': [{
                'id': str(item.pk),
                'product_name': item.product_name,
                'quantity': item.quantity,
                'unit_price': str(item.unit_price),
                'total': str(item.total),
                'modifiers': item.modifiers,
                'notes': item.notes,
                'status': item.status,
                'station': item.station.name if item.station else None,
                'seat_number': item.seat_number,
            } for item in order.items.filter(is_deleted=False).select_related('station')],
        },
    })


@login_required
@require_GET
def api_pending_orders(request):
    hub = _hub_id(request)
    orders = Order.objects.filter(
        hub_id=hub, is_deleted=False,
        status__in=['pending', 'preparing'],
    ).prefetch_related('items').order_by('created_at')

    return JsonResponse({
        'success': True,
        'orders': [{
            'id': str(o.pk),
            'order_number': o.order_number,
            'table': o.table_display,
            'status': o.status,
            'priority': o.priority,
            'item_count': o.item_count,
            'elapsed_minutes': o.elapsed_minutes,
            'is_delayed': o.is_delayed,
        } for o in orders],
    })


@login_required
@require_GET
def api_orders_by_table(request, table_id):
    hub = _hub_id(request)
    orders = Order.objects.filter(
        hub_id=hub, is_deleted=False,
        table_id=table_id,
        status__in=['pending', 'preparing', 'ready'],
    ).prefetch_related('items').order_by('round_number', 'created_at')

    return JsonResponse({
        'success': True,
        'orders': [{
            'id': str(o.pk),
            'order_number': o.order_number,
            'status': o.status,
            'round_number': o.round_number,
            'item_count': o.item_count,
        } for o in orders],
    })


@login_required
@require_GET
def api_station_items(request, station_id):
    hub = _hub_id(request)
    items = OrderItem.objects.filter(
        hub_id=hub, is_deleted=False,
        station_id=station_id,
        status__in=['pending', 'preparing'],
    ).select_related('order').order_by('order__priority', 'created_at')

    return JsonResponse({
        'success': True,
        'items': [{
            'id': str(item.pk),
            'order_number': item.order.order_number,
            'table': item.order.table_display,
            'product_name': item.product_name,
            'quantity': item.quantity,
            'modifiers': item.modifiers,
            'notes': item.notes,
            'status': item.status,
            'priority': item.order.priority,
            'elapsed_minutes': item.order.elapsed_minutes,
            'is_delayed': item.order.is_delayed,
        } for item in items],
    })


@login_required
@require_GET
def api_station_summary(request):
    hub = _hub_id(request)
    stations = KitchenStation.objects.filter(
        hub_id=hub, is_active=True, is_deleted=False,
    )

    return JsonResponse({
        'success': True,
        'stations': [{
            'id': str(s.pk),
            'name': s.name,
            'color': s.color,
            'icon': s.icon,
            'pending_count': s.pending_count,
        } for s in stations],
    })


@login_required
@require_GET
def api_order_stats(request):
    hub = _hub_id(request)
    date_str = request.GET.get('date')

    if date_str:
        from datetime import datetime
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        date = timezone.now().date()

    orders = Order.objects.filter(hub_id=hub, is_deleted=False, created_at__date=date)
    total = orders.count()
    completed = orders.filter(status__in=['served', 'paid']).count()
    cancelled = orders.filter(status='cancelled').count()

    avg_prep = None
    timed_orders = orders.filter(fired_at__isnull=False, ready_at__isnull=False)
    if timed_orders.exists():
        total_seconds = sum(
            (o.ready_at - o.fired_at).total_seconds()
            for o in timed_orders
        )
        avg_prep = int(total_seconds / timed_orders.count() / 60)

    return JsonResponse({
        'success': True,
        'date': date.isoformat(),
        'total_orders': total,
        'completed': completed,
        'cancelled': cancelled,
        'avg_prep_time_minutes': avg_prep,
    })


# =============================================================================
# Settings
# =============================================================================

@login_required
@permission_required('orders.manage_settings')
@with_module_nav('orders', 'settings')
@htmx_view('orders/pages/settings.html', 'orders/partials/settings.html')
def settings(request):
    hub = _hub_id(request)
    config = OrdersSettings.get_settings(hub)

    today = timezone.now().date()
    today_orders = Order.objects.filter(
        hub_id=hub, is_deleted=False, created_at__date=today,
    )
    stations = KitchenStation.objects.filter(
        hub_id=hub, is_deleted=False,
    ).order_by('sort_order', 'name')

    return {
        'config': config,
        'stations': stations,
        'today_orders_count': today_orders.count(),
        'today_revenue': today_orders.filter(status='paid').aggregate(
            total=Sum('total')
        )['total'] or Decimal('0'),
    }


@login_required
@permission_required('orders.manage_settings')
@require_POST
def settings_save(request):
    hub = _hub_id(request)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': _('Invalid JSON')}, status=400)

    config = OrdersSettings.get_settings(hub)
    fields = [
        'auto_print_tickets', 'show_prep_time', 'alert_threshold_minutes',
        'use_rounds', 'auto_fire_on_round', 'sound_on_new_order',
        'default_order_type',
    ]
    for field in fields:
        if field in data:
            setattr(config, field, data[field])
    config.save()
    return JsonResponse({'success': True})


@login_required
@permission_required('orders.manage_settings')
@require_POST
def settings_toggle(request):
    hub = _hub_id(request)
    config = OrdersSettings.get_settings(hub)
    name = request.POST.get('name')
    value = request.POST.get('value') == 'true'

    if hasattr(config, name) and isinstance(getattr(config, name), bool):
        setattr(config, name, value)
        config.save()

    return HttpResponse(status=204)


@login_required
@require_POST
def settings_input(request):
    hub = _hub_id(request)
    config = OrdersSettings.get_settings(hub)
    name = request.POST.get('name')
    value = request.POST.get('value')

    if hasattr(config, name):
        setattr(config, name, int(value))
        config.save()

    return HttpResponse(status=204)


@login_required
@require_POST
def settings_reset(request):
    hub = _hub_id(request)
    config = OrdersSettings.get_settings(hub)
    config.auto_print_tickets = True
    config.show_prep_time = True
    config.alert_threshold_minutes = 15
    config.use_rounds = True
    config.auto_fire_on_round = False
    config.sound_on_new_order = True
    config.default_order_type = 'dine_in'
    config.save()
    return HttpResponse(status=204)
