"""
Integration and E2E tests for Orders module views.
"""

import pytest
import json
from django.urls import resolve

from orders import views
from orders.models import (
    Order,
    OrderItem,
    KitchenStation,
    ProductStation,
    CategoryStation,
    OrdersConfig
)


# ==============================================================================
# URL ROUTING TESTS
# ==============================================================================

@pytest.mark.django_db
class TestURLRouting:
    """Tests for URL routing and resolution."""

    def test_index_url_resolves(self):
        """Test index URL resolves."""
        resolver = resolve('/modules/orders/')
        assert resolver.func == views.index

    def test_kds_url_resolves(self):
        """Test KDS URL resolves."""
        resolver = resolve('/modules/orders/kds/')
        assert resolver.func == views.kitchen_display

    def test_kds_station_url_resolves(self):
        """Test KDS station URL resolves."""
        resolver = resolve('/modules/orders/kds/1/')
        assert resolver.func == views.kitchen_display

    def test_stations_url_resolves(self):
        """Test stations URL resolves."""
        resolver = resolve('/modules/orders/stations/')
        assert resolver.func == views.stations_list

    def test_routing_url_resolves(self):
        """Test routing URL resolves."""
        resolver = resolve('/modules/orders/routing/')
        assert resolver.func == views.routing

    def test_settings_url_resolves(self):
        """Test settings URL resolves."""
        resolver = resolve('/modules/orders/settings/')
        assert resolver.func == views.orders_settings

    def test_api_create_order_url_resolves(self):
        """Test API create order URL resolves."""
        resolver = resolve('/modules/orders/api/orders/create/')
        assert resolver.func == views.api_create_order

    def test_api_pending_orders_url_resolves(self):
        """Test API pending orders URL resolves."""
        resolver = resolve('/modules/orders/api/orders/pending/')
        assert resolver.func == views.api_pending_orders


# ==============================================================================
# AUTHENTICATION TESTS
# ==============================================================================

@pytest.mark.django_db
class TestAuthentication:
    """Tests for view authentication requirements."""

    def test_index_requires_auth(self, client, store_config):
        """Test index requires authentication."""
        response = client.get('/modules/orders/')
        assert response.status_code == 302
        assert '/login/' in response.url

    def test_kds_requires_auth(self, client, store_config):
        """Test KDS requires authentication."""
        response = client.get('/modules/orders/kds/')
        assert response.status_code == 302

    def test_api_create_order_requires_auth(self, client, store_config):
        """Test API create order requires authentication."""
        response = client.post('/modules/orders/api/orders/create/')
        assert response.status_code == 302


# ==============================================================================
# ORDER CRUD E2E TESTS
# ==============================================================================

@pytest.mark.django_db
class TestOrderCRUD:
    """E2E tests for order CRUD operations."""

    def test_create_order_success(self, auth_client, grill_station):
        """Test creating an order with items."""
        response = auth_client.post(
            '/modules/orders/api/orders/create/',
            json.dumps({
                'table_id': 1,
                'created_by': 'Test Waiter',
                'items': [
                    {
                        'product_id': 1,
                        'product_name': 'Burger',
                        'quantity': 2
                    },
                    {
                        'product_id': 2,
                        'product_name': 'Fries',
                        'quantity': 1
                    }
                ]
            }),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True
        assert 'order_id' in data
        assert data['item_count'] == 2

    def test_create_order_without_items_fails(self, auth_client):
        """Test creating order without items fails."""
        response = auth_client.post(
            '/modules/orders/api/orders/create/',
            json.dumps({
                'table_id': 1,
                'items': []
            }),
            content_type='application/json'
        )

        assert response.status_code == 400

    def test_get_order_success(self, auth_client, order_with_items):
        """Test getting an order."""
        response = auth_client.get(
            f'/modules/orders/api/orders/{order_with_items.id}/'
        )

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True
        assert data['order']['order_number'] == order_with_items.order_number
        assert len(data['order']['items']) == 3

    def test_add_item_to_order(self, auth_client, order):
        """Test adding item to existing order."""
        response = auth_client.post(
            f'/modules/orders/api/orders/{order.id}/add-item/',
            json.dumps({
                'product_id': 99,
                'product_name': 'New Item',
                'quantity': 3
            }),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True

        order.refresh_from_db()
        assert order.item_count == 1

    def test_fire_order(self, auth_client, order_with_items):
        """Test firing an order."""
        response = auth_client.post(
            f'/modules/orders/api/orders/{order_with_items.id}/fire/'
        )

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True
        assert data['status'] == 'preparing'

    def test_bump_order(self, auth_client, fired_order):
        """Test bumping an order."""
        response = auth_client.post(
            f'/modules/orders/api/orders/{fired_order.id}/bump/'
        )

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True
        assert data['status'] == 'ready'

    def test_recall_order(self, auth_client, ready_order):
        """Test recalling an order."""
        response = auth_client.post(
            f'/modules/orders/api/orders/{ready_order.id}/recall/'
        )

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['status'] == 'preparing'

    def test_serve_order(self, auth_client, ready_order):
        """Test serving an order."""
        response = auth_client.post(
            f'/modules/orders/api/orders/{ready_order.id}/serve/'
        )

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['status'] == 'served'

    def test_cancel_order(self, auth_client, order):
        """Test cancelling an order."""
        response = auth_client.post(
            f'/modules/orders/api/orders/{order.id}/cancel/',
            {'reason': 'Customer left'}
        )

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['status'] == 'cancelled'

    def test_get_pending_orders(self, auth_client, order, fired_order):
        """Test getting pending orders."""
        response = auth_client.get('/modules/orders/api/orders/pending/')

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True
        assert len(data['orders']) == 2

    def test_get_orders_by_table(self, auth_client, order):
        """Test getting orders for a table."""
        response = auth_client.get(
            f'/modules/orders/api/orders/table/{order.table_id}/'
        )

        assert response.status_code == 200
        data = json.loads(response.content)
        assert len(data['orders']) >= 1


# ==============================================================================
# ORDER ITEM API TESTS
# ==============================================================================

@pytest.mark.django_db
class TestOrderItemAPI:
    """E2E tests for order item operations."""

    def test_bump_item(self, auth_client, order_item):
        """Test bumping a single item."""
        order_item.status = 'preparing'
        order_item.save()

        response = auth_client.post(
            f'/modules/orders/api/items/{order_item.id}/bump/'
        )

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['item_status'] == 'ready'

    def test_cancel_item(self, auth_client, order_item):
        """Test cancelling an item."""
        response = auth_client.post(
            f'/modules/orders/api/items/{order_item.id}/cancel/'
        )

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['status'] == 'cancelled'

    def test_modify_item_quantity(self, auth_client, order_item):
        """Test modifying item quantity."""
        response = auth_client.post(
            f'/modules/orders/api/items/{order_item.id}/quantity/',
            json.dumps({'quantity': 5}),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['quantity'] == 5


# ==============================================================================
# STATION CRUD E2E TESTS
# ==============================================================================

@pytest.mark.django_db
class TestStationCRUD:
    """E2E tests for kitchen station CRUD."""

    def test_create_station_success(self, auth_client):
        """Test creating a kitchen station."""
        response = auth_client.post(
            '/modules/orders/api/stations/create/',
            json.dumps({
                'name': 'Test Station',
                'color': '#FF0000',
                'icon': 'flame-outline'
            }),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True
        assert 'station_id' in data

    def test_create_station_without_name_fails(self, auth_client):
        """Test creating station without name fails."""
        response = auth_client.post(
            '/modules/orders/api/stations/create/',
            json.dumps({'color': '#FF0000'}),
            content_type='application/json'
        )

        assert response.status_code == 400

    def test_create_station_duplicate_name_fails(self, auth_client, grill_station):
        """Test creating station with duplicate name fails."""
        response = auth_client.post(
            '/modules/orders/api/stations/create/',
            json.dumps({'name': 'Grill'}),
            content_type='application/json'
        )

        assert response.status_code == 400

    def test_update_station_success(self, auth_client, grill_station):
        """Test updating a station."""
        response = auth_client.post(
            f'/modules/orders/api/stations/{grill_station.id}/update/',
            json.dumps({
                'name': 'Hot Grill',
                'color': '#FF5500'
            }),
            content_type='application/json'
        )

        assert response.status_code == 200

        grill_station.refresh_from_db()
        assert grill_station.name == 'Hot Grill'
        assert grill_station.color == '#FF5500'

    def test_delete_station(self, auth_client, grill_station):
        """Test deleting a station (soft delete)."""
        response = auth_client.post(
            f'/modules/orders/api/stations/{grill_station.id}/delete/'
        )

        assert response.status_code == 200

        grill_station.refresh_from_db()
        assert grill_station.is_active is False

    def test_list_stations(self, auth_client, grill_station, bar_station):
        """Test listing stations."""
        response = auth_client.get('/modules/orders/api/stations/')

        assert response.status_code == 200
        data = json.loads(response.content)
        assert len(data['stations']) == 2

    def test_get_station_items(self, auth_client, order_with_items, grill_station):
        """Test getting items for a station."""
        response = auth_client.get(
            f'/modules/orders/api/stations/{grill_station.id}/items/'
        )

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True

    def test_get_station_summary(self, auth_client, grill_station, bar_station):
        """Test getting station summary."""
        response = auth_client.get('/modules/orders/api/stations/summary/')

        assert response.status_code == 200
        data = json.loads(response.content)
        assert len(data['stations']) == 2


# ==============================================================================
# ROUTING API E2E TESTS
# ==============================================================================

@pytest.mark.django_db
class TestRoutingAPI:
    """E2E tests for routing API."""

    def test_assign_product_station(self, auth_client, grill_station):
        """Test assigning product to station."""
        response = auth_client.post(
            '/modules/orders/api/routing/product/',
            json.dumps({
                'product_id': 100,
                'station_id': grill_station.id
            }),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True

    def test_assign_category_station(self, auth_client, bar_station):
        """Test assigning category to station."""
        response = auth_client.post(
            '/modules/orders/api/routing/category/',
            json.dumps({
                'category_id': 10,
                'station_id': bar_station.id
            }),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True

    def test_remove_product_routing(self, auth_client, product_mapping):
        """Test removing product routing."""
        response = auth_client.post(
            f'/modules/orders/api/routing/product/{product_mapping.product_id}/remove/'
        )

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['deleted'] is True

    def test_remove_category_routing(self, auth_client, category_mapping):
        """Test removing category routing."""
        response = auth_client.post(
            f'/modules/orders/api/routing/category/{category_mapping.category_id}/remove/'
        )

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['deleted'] is True


# ==============================================================================
# STATS API TESTS
# ==============================================================================

@pytest.mark.django_db
class TestStatsAPI:
    """E2E tests for stats API."""

    def test_get_order_stats(self, auth_client, order, fired_order, ready_order):
        """Test getting order statistics."""
        response = auth_client.get('/modules/orders/api/orders/stats/')

        assert response.status_code == 200
        data = json.loads(response.content)
        assert 'total_orders' in data
        assert 'completed' in data

    def test_get_order_stats_with_date(self, auth_client):
        """Test getting stats for specific date."""
        from django.utils import timezone
        today = timezone.now().strftime('%Y-%m-%d')

        response = auth_client.get(f'/modules/orders/api/orders/stats/?date={today}')

        assert response.status_code == 200


# ==============================================================================
# SETTINGS API TESTS
# ==============================================================================

@pytest.mark.django_db
class TestSettingsAPI:
    """E2E tests for settings API."""

    def test_settings_save_success(self, auth_client, orders_config):
        """Test saving settings."""
        response = auth_client.post(
            '/modules/orders/settings/save/',
            json.dumps({
                'auto_print_tickets': False,
                'alert_threshold_minutes': 20,
                'use_rounds': False
            }),
            content_type='application/json'
        )

        assert response.status_code == 200

        config = OrdersConfig.get_config()
        assert config.auto_print_tickets is False
        assert config.alert_threshold_minutes == 20
        assert config.use_rounds is False

    def test_settings_toggle(self, auth_client, orders_config):
        """Test toggling a boolean setting."""
        response = auth_client.post(
            '/modules/orders/settings/toggle/',
            {'name': 'auto_print_tickets', 'value': 'false'}
        )

        assert response.status_code == 204

        config = OrdersConfig.get_config()
        assert config.auto_print_tickets is False

    def test_settings_input(self, auth_client, orders_config):
        """Test updating a numeric setting."""
        response = auth_client.post(
            '/modules/orders/settings/input/',
            {'name': 'alert_threshold_minutes', 'value': '30'}
        )

        assert response.status_code == 204

        config = OrdersConfig.get_config()
        assert config.alert_threshold_minutes == 30

    def test_settings_reset(self, auth_client, orders_config):
        """Test resetting settings to defaults."""
        # First change settings
        orders_config.alert_threshold_minutes = 30
        orders_config.auto_print_tickets = False
        orders_config.save()

        response = auth_client.post('/modules/orders/settings/reset/')
        assert response.status_code == 204

        config = OrdersConfig.get_config()
        assert config.alert_threshold_minutes == 15
        assert config.auto_print_tickets is True
