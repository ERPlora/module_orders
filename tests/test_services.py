"""
Unit tests for Orders module services.
"""

import pytest
from django.utils import timezone
from datetime import timedelta

from orders.models import (
    Order,
    OrderItem,
    KitchenStation,
    ProductStation,
    CategoryStation
)
from orders.services import OrderService


# ==============================================================================
# CREATE ORDER TESTS
# ==============================================================================

@pytest.mark.django_db
class TestCreateOrder:
    """Tests for create_order method."""

    def test_create_order_basic(self):
        """Test creating a basic order."""
        order = OrderService.create_order(
            table_id=1,
            created_by='Test Waiter'
        )

        assert order.id is not None
        assert order.table_id == 1
        assert order.created_by == 'Test Waiter'
        assert order.status == Order.STATUS_PENDING

    def test_create_order_with_items(self, grill_station):
        """Test creating an order with items."""
        items = [
            {
                'product_id': 1,
                'product_name': 'Burger',
                'quantity': 2,
                'station': grill_station
            },
            {
                'product_id': 2,
                'product_name': 'Fries',
                'quantity': 1
            }
        ]

        order = OrderService.create_order(
            table_id=1,
            items=items,
            created_by='John'
        )

        assert order.item_count == 2
        burger_item = order.items.get(product_name='Burger')
        assert burger_item.quantity == 2
        assert burger_item.station == grill_station

    def test_create_order_with_notes(self):
        """Test creating order with notes."""
        order = OrderService.create_order(
            table_id=1,
            notes='VIP customer',
            round_number=2
        )

        assert order.notes == 'VIP customer'
        assert order.round_number == 2


# ==============================================================================
# ADD ITEM TESTS
# ==============================================================================

@pytest.mark.django_db
class TestAddItem:
    """Tests for add_item_to_order method."""

    def test_add_item_basic(self, order):
        """Test adding an item to an order."""
        item = OrderService.add_item_to_order(
            order=order,
            product_id=1,
            product_name='Test Product',
            quantity=2
        )

        assert item.id is not None
        assert item.order == order
        assert item.quantity == 2

    def test_add_item_with_modifiers(self, order):
        """Test adding item with modifiers and notes."""
        item = OrderService.add_item_to_order(
            order=order,
            product_id=1,
            product_name='Burger',
            modifiers='No onions, Extra cheese',
            notes='Allergy: peanuts'
        )

        assert item.modifiers == 'No onions, Extra cheese'
        assert item.notes == 'Allergy: peanuts'

    def test_add_item_auto_routing(self, order, grill_station):
        """Test that auto_route assigns station from mapping."""
        ProductStation.objects.create(
            product_id=100,
            station=grill_station
        )

        item = OrderService.add_item_to_order(
            order=order,
            product_id=100,
            product_name='Steak',
            auto_route=True
        )

        assert item.station == grill_station


# ==============================================================================
# ORDER OPERATIONS TESTS
# ==============================================================================

@pytest.mark.django_db
class TestOrderOperations:
    """Tests for order operation methods."""

    def test_fire_order(self, order_with_items):
        """Test firing an order."""
        result = OrderService.fire_order(order_with_items.id)

        assert result.status == Order.STATUS_PREPARING
        assert result.fired_at is not None

        # All items should be preparing
        for item in result.items.all():
            assert item.status == OrderItem.STATUS_PREPARING

    def test_bump_item(self, order_item):
        """Test bumping a single item."""
        order_item.status = OrderItem.STATUS_PREPARING
        order_item.started_at = timezone.now()
        order_item.save()

        result = OrderService.bump_item(order_item.id)

        assert result.status == OrderItem.STATUS_READY
        assert result.completed_at is not None

    def test_bump_order(self, order_with_items):
        """Test bumping entire order."""
        # Fire first
        order_with_items.fire()

        result = OrderService.bump_order(order_with_items.id)

        assert result.status == Order.STATUS_READY
        for item in result.items.all():
            assert item.status == OrderItem.STATUS_READY

    def test_recall_order(self, ready_order):
        """Test recalling a ready order."""
        result = OrderService.recall_order(ready_order.id)

        assert result.status == Order.STATUS_PREPARING
        assert result.ready_at is None

    def test_cancel_order(self, order_with_items):
        """Test cancelling an order."""
        result = OrderService.cancel_order(order_with_items.id, 'Customer left')

        assert result.status == Order.STATUS_CANCELLED
        for item in result.items.all():
            assert item.status == OrderItem.STATUS_CANCELLED

    def test_cancel_item(self, order_item):
        """Test cancelling a single item."""
        result = OrderService.cancel_item(order_item.id)

        assert result.status == OrderItem.STATUS_CANCELLED

    def test_modify_item_quantity(self, order_item):
        """Test modifying item quantity."""
        result = OrderService.modify_item_quantity(order_item.id, 5)

        assert result.quantity == 5

    def test_modify_item_quantity_minimum(self, order_item):
        """Test quantity cannot go below 1."""
        result = OrderService.modify_item_quantity(order_item.id, 0)

        assert result.quantity == 1


# ==============================================================================
# QUERY METHODS TESTS
# ==============================================================================

@pytest.mark.django_db
class TestQueryMethods:
    """Tests for query methods."""

    def test_get_pending_orders(self, order, fired_order):
        """Test getting pending orders."""
        orders = OrderService.get_pending_orders()

        assert len(orders) == 2

    def test_get_orders_by_table(self, order):
        """Test getting orders for a table."""
        orders = OrderService.get_orders_by_table(order.table_id)

        assert len(orders) == 1
        assert orders[0].id == order.id

    def test_get_orders_by_station(self, order_with_items, grill_station):
        """Test getting items for a station."""
        # Fire the order so items are preparing
        order_with_items.fire()

        items = OrderService.get_orders_by_station(grill_station.id)

        # Grill station has burger and fries
        assert len(items) == 2

    def test_get_station_summary(self, order_with_items, grill_station, bar_station):
        """Test getting station summary."""
        summary = OrderService.get_station_summary()

        assert len(summary) >= 2
        grill_summary = next(s for s in summary if s['name'] == 'Grill')
        assert grill_summary['pending_count'] == 2  # Burger + Fries


# ==============================================================================
# ROUTING TESTS
# ==============================================================================

@pytest.mark.django_db
class TestRouting:
    """Tests for routing methods."""

    def test_assign_product_to_station(self, grill_station):
        """Test assigning product to station."""
        mapping = OrderService.assign_product_to_station(50, grill_station.id)

        assert mapping.product_id == 50
        assert mapping.station == grill_station

    def test_assign_product_updates_existing(self, grill_station, bar_station):
        """Test that assigning updates existing mapping."""
        OrderService.assign_product_to_station(50, grill_station.id)
        mapping = OrderService.assign_product_to_station(50, bar_station.id)

        assert mapping.station == bar_station
        assert ProductStation.objects.filter(product_id=50).count() == 1

    def test_assign_category_to_station(self, bar_station):
        """Test assigning category to station."""
        mapping = OrderService.assign_category_to_station(10, bar_station.id)

        assert mapping.category_id == 10
        assert mapping.station == bar_station

    def test_get_station_for_product_direct(self, grill_station):
        """Test getting station from direct product mapping."""
        ProductStation.objects.create(
            product_id=100,
            station=grill_station
        )

        station = OrderService.get_station_for_product(100)

        assert station == grill_station

    def test_get_station_for_product_none(self):
        """Test getting station for unmapped product."""
        station = OrderService.get_station_for_product(9999)

        assert station is None


# ==============================================================================
# STATS TESTS
# ==============================================================================

@pytest.mark.django_db
class TestStats:
    """Tests for statistics methods."""

    def test_get_order_stats(self, order, fired_order, ready_order):
        """Test getting order statistics."""
        # Mark ready order as served
        ready_order.status = Order.STATUS_SERVED
        ready_order.save()

        stats = OrderService.get_order_stats()

        assert stats['total_orders'] == 3
        assert stats['completed'] == 1  # Only served

    def test_get_order_stats_specific_date(self):
        """Test getting stats for specific date."""
        stats = OrderService.get_order_stats(timezone.now().date())

        assert 'total_orders' in stats
        assert 'completed' in stats
        assert 'cancelled' in stats
