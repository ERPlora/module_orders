"""
Pytest fixtures for Orders module tests.
"""

import pytest
from decimal import Decimal
from django.conf import settings
from django.utils import timezone

# Disable debug toolbar during tests
if 'debug_toolbar' in settings.INSTALLED_APPS:
    settings.INSTALLED_APPS = [
        app for app in settings.INSTALLED_APPS if app != 'debug_toolbar'
    ]
if hasattr(settings, 'MIDDLEWARE'):
    settings.MIDDLEWARE = [
        m for m in settings.MIDDLEWARE
        if 'debug_toolbar' not in m
    ]

from django.contrib.auth.hashers import make_password
from apps.accounts.models import LocalUser
from apps.configuration.models import StoreConfig

from orders.models import (
    OrdersConfig,
    KitchenStation,
    Order,
    OrderItem,
    ProductStation,
    CategoryStation
)


@pytest.fixture
def local_user(db):
    """Create a test user."""
    return LocalUser.objects.create(
        name='Test User',
        email='test@example.com',
        role='admin',
        pin_hash=make_password('1234'),
        is_active=True
    )


@pytest.fixture
def user(local_user):
    """Alias for local_user fixture."""
    return local_user


@pytest.fixture
def store_config(db):
    """Create store config for tests."""
    config = StoreConfig.get_config()
    config.is_configured = True
    config.name = 'Test Store'
    config.save()
    return config


@pytest.fixture
def auth_client(client, local_user, store_config):
    """Return an authenticated client."""
    session = client.session
    session['local_user_id'] = str(local_user.id)
    session['user_name'] = local_user.name
    session['user_email'] = local_user.email
    session['user_role'] = local_user.role
    session['store_config_checked'] = True
    session.save()
    return client


@pytest.fixture
def orders_config(db):
    """Create orders config."""
    return OrdersConfig.get_config()


@pytest.fixture
def grill_station(db):
    """Create a grill kitchen station."""
    return KitchenStation.objects.create(
        name='Grill',
        name_es='Parrilla',
        color='#EF4444',
        icon='flame-outline',
        order=1
    )


@pytest.fixture
def bar_station(db):
    """Create a bar kitchen station."""
    return KitchenStation.objects.create(
        name='Bar',
        color='#3B82F6',
        icon='beer-outline',
        order=2
    )


@pytest.fixture
def dessert_station(db):
    """Create a dessert kitchen station."""
    return KitchenStation.objects.create(
        name='Dessert',
        name_es='Postres',
        color='#EC4899',
        icon='ice-cream-outline',
        order=3
    )


@pytest.fixture
def order(db):
    """Create a basic pending order."""
    return Order.objects.create(
        order_number=Order.generate_order_number(),
        table_id=1,
        created_by='John',
        status=Order.STATUS_PENDING
    )


@pytest.fixture
def fired_order(db):
    """Create a fired (in-preparation) order."""
    return Order.objects.create(
        order_number=Order.generate_order_number(),
        table_id=2,
        created_by='Jane',
        status=Order.STATUS_PREPARING,
        fired_at=timezone.now()
    )


@pytest.fixture
def ready_order(db):
    """Create a ready order."""
    return Order.objects.create(
        order_number=Order.generate_order_number(),
        table_id=3,
        status=Order.STATUS_READY,
        fired_at=timezone.now() - timezone.timedelta(minutes=10),
        ready_at=timezone.now()
    )


@pytest.fixture
def order_with_items(db, order, grill_station, bar_station):
    """Create an order with items."""
    OrderItem.objects.create(
        order=order,
        product_id=1,
        product_name='Burger',
        quantity=2,
        station=grill_station,
        status=OrderItem.STATUS_PENDING
    )
    OrderItem.objects.create(
        order=order,
        product_id=2,
        product_name='Beer',
        quantity=2,
        station=bar_station,
        status=OrderItem.STATUS_PENDING
    )
    OrderItem.objects.create(
        order=order,
        product_id=3,
        product_name='Fries',
        quantity=1,
        station=grill_station,
        modifiers='Extra crispy',
        status=OrderItem.STATUS_PENDING
    )
    return order


@pytest.fixture
def order_item(order, grill_station):
    """Create a single order item."""
    return OrderItem.objects.create(
        order=order,
        product_id=1,
        product_name='Steak',
        quantity=1,
        station=grill_station,
        status=OrderItem.STATUS_PENDING
    )


@pytest.fixture
def product_mapping(db, grill_station):
    """Create a product-station mapping."""
    return ProductStation.objects.create(
        product_id=100,
        station=grill_station
    )


@pytest.fixture
def category_mapping(db, bar_station):
    """Create a category-station mapping."""
    return CategoryStation.objects.create(
        category_id=10,
        station=bar_station
    )
