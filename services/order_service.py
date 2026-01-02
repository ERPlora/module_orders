"""
Order Service

Handles business logic for order operations.
"""

from typing import List, Optional, Dict, Any
from django.db import transaction
from django.utils import timezone

from ..models import (
    Order,
    OrderItem,
    KitchenStation,
    ProductStation,
    CategoryStation,
    OrdersConfig
)


class OrderService:
    """Service for managing orders."""

    @staticmethod
    def get_station_for_product(product_id: int) -> Optional[KitchenStation]:
        """
        Get the kitchen station for a product.

        Priority:
        1. Direct product mapping
        2. Category mapping
        3. None (default station or no routing)
        """
        # Check direct product mapping
        station = ProductStation.get_station_for_product(product_id)
        if station:
            return station

        # Check category mapping
        try:
            from inventory.models import Product
            product = Product.objects.get(pk=product_id)
            for category in product.categories.all():
                station = CategoryStation.get_station_for_category(category.id)
                if station:
                    return station
        except Exception:
            pass

        return None

    @staticmethod
    @transaction.atomic
    def create_order(
        table_id: int = None,
        sale_id: int = None,
        items: List[Dict] = None,
        created_by: str = '',
        round_number: int = 1,
        notes: str = '',
        auto_route: bool = True
    ) -> Order:
        """
        Create a new order with items.

        Args:
            table_id: Table ID (optional)
            sale_id: Sale ID (optional)
            items: List of item dicts with product_id, quantity, etc.
            created_by: Waiter/server name
            round_number: Course number
            notes: Order notes
            auto_route: Automatically route items to stations

        Returns:
            Created Order instance
        """
        order = Order.create_order(
            table_id=table_id,
            sale_id=sale_id,
            created_by=created_by,
            round_number=round_number,
            notes=notes
        )

        if items:
            for item_data in items:
                product_id = item_data.get('product_id')
                product_name = item_data.get('product_name', f'Product {product_id}')
                quantity = item_data.get('quantity', 1)

                # Get station for routing
                station = None
                if auto_route:
                    station = item_data.get('station')
                    if not station:
                        station = OrderService.get_station_for_product(product_id)

                OrderItem.add_to_order(
                    order=order,
                    product_id=product_id,
                    product_name=product_name,
                    quantity=quantity,
                    station=station,
                    modifiers=item_data.get('modifiers', ''),
                    notes=item_data.get('notes', ''),
                    seat_number=item_data.get('seat_number')
                )

        return order

    @staticmethod
    def add_item_to_order(
        order: Order,
        product_id: int,
        product_name: str,
        quantity: int = 1,
        modifiers: str = '',
        notes: str = '',
        seat_number: int = None,
        auto_route: bool = True
    ) -> OrderItem:
        """Add an item to an existing order."""
        station = None
        if auto_route:
            station = OrderService.get_station_for_product(product_id)

        return OrderItem.add_to_order(
            order=order,
            product_id=product_id,
            product_name=product_name,
            quantity=quantity,
            station=station,
            modifiers=modifiers,
            notes=notes,
            seat_number=seat_number
        )

    @staticmethod
    def get_pending_orders() -> List[Order]:
        """Get all pending/preparing orders."""
        return list(Order.objects.filter(
            status__in=[Order.STATUS_PENDING, Order.STATUS_PREPARING]
        ).prefetch_related('items', 'items__station').order_by('created_at'))

    @staticmethod
    def get_orders_by_table(table_id: int) -> List[Order]:
        """Get all active orders for a table."""
        return list(Order.objects.filter(
            table_id=table_id,
            status__in=[Order.STATUS_PENDING, Order.STATUS_PREPARING, Order.STATUS_READY]
        ).prefetch_related('items').order_by('round_number', 'created_at'))

    @staticmethod
    def get_orders_by_station(station_id: int) -> List[Dict]:
        """Get pending items for a kitchen station."""
        items = OrderItem.objects.filter(
            station_id=station_id,
            status__in=[OrderItem.STATUS_PENDING, OrderItem.STATUS_PREPARING]
        ).select_related('order').order_by('order__priority', 'created_at')

        return [
            {
                'id': item.id,
                'order_number': item.order.order_number,
                'table': item.order.table_display,
                'product_name': item.product_name,
                'quantity': item.quantity,
                'modifiers': item.modifiers,
                'notes': item.notes,
                'status': item.status,
                'priority': item.order.priority,
                'elapsed_minutes': item.order.elapsed_minutes,
                'is_delayed': item.order.is_delayed
            }
            for item in items
        ]

    @staticmethod
    def get_station_summary() -> List[Dict]:
        """Get summary of pending items per station."""
        stations = KitchenStation.objects.filter(is_active=True)

        return [
            {
                'id': station.id,
                'name': station.name,
                'color': station.color,
                'icon': station.icon,
                'pending_count': station.pending_count
            }
            for station in stations
        ]

    @staticmethod
    def fire_order(order_id: int) -> Order:
        """Fire an order (send to kitchen)."""
        order = Order.objects.get(pk=order_id)
        return order.fire()

    @staticmethod
    def bump_item(item_id: int) -> OrderItem:
        """Bump (mark ready) a single item."""
        item = OrderItem.objects.get(pk=item_id)
        return item.mark_ready()

    @staticmethod
    def bump_order(order_id: int) -> Order:
        """Bump (mark ready) an entire order."""
        order = Order.objects.get(pk=order_id)

        # Mark all items as ready
        order.items.filter(
            status__in=[OrderItem.STATUS_PENDING, OrderItem.STATUS_PREPARING]
        ).update(
            status=OrderItem.STATUS_READY,
            completed_at=timezone.now()
        )

        return order.mark_ready()

    @staticmethod
    def recall_order(order_id: int) -> Order:
        """Recall a ready order back to preparing."""
        order = Order.objects.get(pk=order_id)

        if order.status == Order.STATUS_READY:
            order.status = Order.STATUS_PREPARING
            order.ready_at = None
            order.save()

            order.items.filter(status=OrderItem.STATUS_READY).update(
                status=OrderItem.STATUS_PREPARING,
                completed_at=None
            )

        return order

    @staticmethod
    def cancel_order(order_id: int, reason: str = '') -> Order:
        """Cancel an order."""
        order = Order.objects.get(pk=order_id)
        return order.cancel(reason)

    @staticmethod
    def cancel_item(item_id: int) -> OrderItem:
        """Cancel a single item."""
        item = OrderItem.objects.get(pk=item_id)
        return item.cancel()

    @staticmethod
    def modify_item_quantity(item_id: int, quantity: int) -> OrderItem:
        """Modify the quantity of an item."""
        item = OrderItem.objects.get(pk=item_id)
        item.quantity = max(1, quantity)
        item.save()
        return item

    @staticmethod
    def assign_product_to_station(product_id: int, station_id: int) -> ProductStation:
        """Assign a product to a kitchen station."""
        station = KitchenStation.objects.get(pk=station_id)
        mapping, _ = ProductStation.objects.update_or_create(
            product_id=product_id,
            defaults={'station': station}
        )
        return mapping

    @staticmethod
    def assign_category_to_station(category_id: int, station_id: int) -> CategoryStation:
        """Assign a category to a kitchen station."""
        station = KitchenStation.objects.get(pk=station_id)
        mapping, _ = CategoryStation.objects.update_or_create(
            category_id=category_id,
            defaults={'station': station}
        )
        return mapping

    @staticmethod
    def get_order_stats(date=None) -> Dict[str, Any]:
        """Get order statistics for a date."""
        from django.db.models import Count, Avg
        from django.db.models.functions import Extract

        if date is None:
            date = timezone.now().date()

        orders = Order.objects.filter(
            created_at__date=date
        )

        total = orders.count()
        completed = orders.filter(status__in=[Order.STATUS_SERVED]).count()
        cancelled = orders.filter(status=Order.STATUS_CANCELLED).count()

        # Average prep time (orders that have both fired_at and ready_at)
        completed_orders = orders.filter(
            fired_at__isnull=False,
            ready_at__isnull=False
        )

        avg_prep = None
        if completed_orders.exists():
            from django.db.models import F, ExpressionWrapper, DurationField
            orders_with_duration = completed_orders.annotate(
                prep_duration=ExpressionWrapper(
                    F('ready_at') - F('fired_at'),
                    output_field=DurationField()
                )
            )
            total_seconds = sum(
                o.prep_duration.total_seconds() for o in orders_with_duration
            )
            avg_prep = int(total_seconds / completed_orders.count() / 60)

        return {
            'date': date.isoformat(),
            'total_orders': total,
            'completed': completed,
            'cancelled': cancelled,
            'avg_prep_time_minutes': avg_prep
        }
