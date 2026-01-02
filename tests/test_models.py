"""
Unit tests for Orders module models.
"""

import pytest
from django.db import IntegrityError
from django.utils import timezone
from datetime import timedelta

from orders.models import (
    OrdersConfig,
    KitchenStation,
    Order,
    OrderItem,
    ProductStation,
    CategoryStation
)


# ==============================================================================
# ORDERS CONFIG TESTS
# ==============================================================================

@pytest.mark.django_db
class TestOrdersConfig:
    """Tests for OrdersConfig model."""

    def test_get_config_creates_singleton(self):
        """Test get_config creates singleton if not exists."""
        config = OrdersConfig.get_config()
        assert config is not None
        assert config.pk == 1

    def test_get_config_returns_existing(self):
        """Test get_config returns existing config."""
        config1 = OrdersConfig.get_config()
        config1.alert_threshold_minutes = 20
        config1.save()

        config2 = OrdersConfig.get_config()
        assert config2.alert_threshold_minutes == 20

    def test_config_defaults(self):
        """Test default config values."""
        config = OrdersConfig.get_config()
        assert config.auto_print_tickets is True
        assert config.show_prep_time is True
        assert config.alert_threshold_minutes == 15
        assert config.use_rounds is True

    def test_config_str(self):
        """Test config string representation."""
        config = OrdersConfig.get_config()
        assert str(config) == "Orders Configuration"


# ==============================================================================
# KITCHEN STATION TESTS
# ==============================================================================

@pytest.mark.django_db
class TestKitchenStation:
    """Tests for KitchenStation model."""

    def test_create_station(self):
        """Test creating a kitchen station."""
        station = KitchenStation.objects.create(
            name='Test Station',
            color='#FF0000'
        )
        assert station.id is not None
        assert station.name == 'Test Station'
        assert station.is_active is True

    def test_station_str(self):
        """Test station string representation."""
        station = KitchenStation.objects.create(name='Grill')
        assert str(station) == 'Grill'

    def test_station_unique_name(self):
        """Test station names must be unique."""
        KitchenStation.objects.create(name='Bar')
        with pytest.raises(IntegrityError):
            KitchenStation.objects.create(name='Bar')

    def test_station_pending_count(self, grill_station, order):
        """Test pending_count property."""
        OrderItem.objects.create(
            order=order,
            product_id=1,
            product_name='Burger',
            station=grill_station,
            status=OrderItem.STATUS_PENDING
        )
        OrderItem.objects.create(
            order=order,
            product_id=2,
            product_name='Steak',
            station=grill_station,
            status=OrderItem.STATUS_PREPARING
        )
        OrderItem.objects.create(
            order=order,
            product_id=3,
            product_name='Done Item',
            station=grill_station,
            status=OrderItem.STATUS_READY
        )

        assert grill_station.pending_count == 2  # Pending + Preparing


# ==============================================================================
# ORDER TESTS
# ==============================================================================

@pytest.mark.django_db
class TestOrder:
    """Tests for Order model."""

    def test_create_order(self):
        """Test creating an order."""
        order = Order.objects.create(
            order_number='TEST-001',
            table_id=1
        )
        assert order.id is not None
        assert order.status == Order.STATUS_PENDING

    def test_order_str(self):
        """Test order string representation."""
        order = Order.objects.create(order_number='ORD-123')
        assert str(order) == 'Order #ORD-123'

    def test_generate_order_number(self):
        """Test order number generation."""
        number = Order.generate_order_number()
        assert number is not None
        assert '-' in number

    def test_order_unique_number(self):
        """Test order numbers must be unique."""
        Order.objects.create(order_number='DUP-001')
        with pytest.raises(IntegrityError):
            Order.objects.create(order_number='DUP-001')

    def test_table_display_with_id(self, order):
        """Test table_display with table_id."""
        # table_display returns '-' when table module isn't available
        assert order.table_display is not None

    def test_elapsed_minutes_before_fire(self, order):
        """Test elapsed_minutes returns 0 before firing."""
        assert order.elapsed_minutes == 0

    def test_elapsed_minutes_after_fire(self, fired_order):
        """Test elapsed_minutes after firing."""
        fired_order.fired_at = timezone.now() - timedelta(minutes=5)
        fired_order.save()
        assert fired_order.elapsed_minutes >= 5

    def test_prep_time_minutes(self, ready_order):
        """Test prep_time_minutes calculation."""
        ready_order.fired_at = timezone.now() - timedelta(minutes=10)
        ready_order.ready_at = timezone.now()
        ready_order.save()
        assert ready_order.prep_time_minutes == 10

    def test_is_delayed(self, orders_config, order):
        """Test is_delayed property."""
        orders_config.alert_threshold_minutes = 5
        orders_config.save()

        order.fired_at = timezone.now() - timedelta(minutes=10)
        order.status = Order.STATUS_PREPARING
        order.save()

        assert order.is_delayed is True

    def test_item_count(self, order_with_items):
        """Test item_count property."""
        assert order_with_items.item_count == 3

    def test_fire_order(self, order):
        """Test firing an order."""
        order.fire()

        assert order.status == Order.STATUS_PREPARING
        assert order.fired_at is not None

    def test_mark_ready(self, fired_order):
        """Test marking order as ready."""
        fired_order.mark_ready()

        assert fired_order.status == Order.STATUS_READY
        assert fired_order.ready_at is not None

    def test_mark_served(self, ready_order):
        """Test marking order as served."""
        ready_order.mark_served()

        assert ready_order.status == Order.STATUS_SERVED
        assert ready_order.served_at is not None

    def test_cancel_order(self, order):
        """Test cancelling an order."""
        order.cancel('Customer left')

        assert order.status == Order.STATUS_CANCELLED
        assert 'Customer left' in order.notes

    def test_create_order_class_method(self):
        """Test create_order class method."""
        order = Order.create_order(
            table_id=5,
            created_by='Test Waiter',
            notes='VIP customer'
        )

        assert order.id is not None
        assert order.table_id == 5
        assert order.created_by == 'Test Waiter'
        assert order.order_number is not None


# ==============================================================================
# ORDER ITEM TESTS
# ==============================================================================

@pytest.mark.django_db
class TestOrderItem:
    """Tests for OrderItem model."""

    def test_create_item(self, order):
        """Test creating an order item."""
        item = OrderItem.objects.create(
            order=order,
            product_id=1,
            product_name='Test Product',
            quantity=2
        )
        assert item.id is not None
        assert item.status == OrderItem.STATUS_PENDING

    def test_item_str(self, order):
        """Test item string representation."""
        item = OrderItem.objects.create(
            order=order,
            product_id=1,
            product_name='Burger',
            quantity=2
        )
        assert str(item) == '2x Burger'

    def test_display_name_without_modifiers(self, order_item):
        """Test display_name without modifiers."""
        assert order_item.display_name == order_item.product_name

    def test_display_name_with_modifiers(self, order):
        """Test display_name with modifiers."""
        item = OrderItem.objects.create(
            order=order,
            product_id=1,
            product_name='Burger',
            quantity=1,
            modifiers='No onions'
        )
        assert 'No onions' in item.display_name

    def test_prep_time_minutes(self, order_item):
        """Test prep_time_minutes calculation."""
        order_item.started_at = timezone.now() - timedelta(minutes=5)
        order_item.completed_at = timezone.now()
        order_item.save()

        assert order_item.prep_time_minutes == 5

    def test_start_preparing(self, order_item):
        """Test start_preparing method."""
        order_item.start_preparing()

        assert order_item.status == OrderItem.STATUS_PREPARING
        assert order_item.started_at is not None

    def test_mark_ready(self, order_item):
        """Test mark_ready method."""
        order_item.started_at = timezone.now()
        order_item.save()
        order_item.mark_ready()

        assert order_item.status == OrderItem.STATUS_READY
        assert order_item.completed_at is not None

    def test_mark_ready_completes_order(self, order):
        """Test that marking last item ready completes the order."""
        item = OrderItem.objects.create(
            order=order,
            product_id=1,
            product_name='Single Item',
            status=OrderItem.STATUS_PREPARING
        )
        order.status = Order.STATUS_PREPARING
        order.fired_at = timezone.now()
        order.save()

        item.mark_ready()

        order.refresh_from_db()
        assert order.status == Order.STATUS_READY

    def test_cancel_item(self, order_item):
        """Test cancel method."""
        order_item.cancel()

        assert order_item.status == OrderItem.STATUS_CANCELLED

    def test_add_to_order_class_method(self, order, grill_station):
        """Test add_to_order class method."""
        item = OrderItem.add_to_order(
            order=order,
            product_id=50,
            product_name='Test Product',
            quantity=3,
            station=grill_station,
            modifiers='Well done',
            notes='Allergy alert'
        )

        assert item.id is not None
        assert item.product_id == 50
        assert item.quantity == 3
        assert item.station == grill_station


# ==============================================================================
# PRODUCT STATION TESTS
# ==============================================================================

@pytest.mark.django_db
class TestProductStation:
    """Tests for ProductStation model."""

    def test_create_mapping(self, grill_station):
        """Test creating a product-station mapping."""
        mapping = ProductStation.objects.create(
            product_id=1,
            station=grill_station
        )
        assert mapping.id is not None

    def test_mapping_str(self, product_mapping):
        """Test mapping string representation."""
        result = str(product_mapping)
        assert 'Product 100' in result
        assert 'Grill' in result

    def test_unique_product(self, grill_station, bar_station):
        """Test product can only be mapped once."""
        ProductStation.objects.create(
            product_id=999,
            station=grill_station
        )
        with pytest.raises(IntegrityError):
            ProductStation.objects.create(
                product_id=999,
                station=bar_station
            )

    def test_get_station_for_product(self, product_mapping):
        """Test get_station_for_product class method."""
        station = ProductStation.get_station_for_product(100)
        assert station.name == 'Grill'

    def test_get_station_for_product_not_found(self):
        """Test get_station_for_product returns None for unmapped product."""
        station = ProductStation.get_station_for_product(9999)
        assert station is None


# ==============================================================================
# CATEGORY STATION TESTS
# ==============================================================================

@pytest.mark.django_db
class TestCategoryStation:
    """Tests for CategoryStation model."""

    def test_create_mapping(self, bar_station):
        """Test creating a category-station mapping."""
        mapping = CategoryStation.objects.create(
            category_id=1,
            station=bar_station
        )
        assert mapping.id is not None

    def test_unique_category(self, grill_station, bar_station):
        """Test category can only be mapped once."""
        CategoryStation.objects.create(
            category_id=999,
            station=grill_station
        )
        with pytest.raises(IntegrityError):
            CategoryStation.objects.create(
                category_id=999,
                station=bar_station
            )

    def test_get_station_for_category(self, category_mapping):
        """Test get_station_for_category class method."""
        station = CategoryStation.get_station_for_category(10)
        assert station.name == 'Bar'

    def test_get_station_for_category_not_found(self):
        """Test get_station_for_category returns None for unmapped category."""
        station = CategoryStation.get_station_for_category(9999)
        assert station is None
