"""
Orders Module Models

Order/ticket management for hospitality businesses.
Features:
- Order tickets with items routed to kitchen stations
- Round/course support for multi-course meals
- Priority levels (normal, rush, VIP)
- Fire/bump/recall/serve workflow
- Kitchen station routing (product and category based)
- Order types (dine-in, takeaway, delivery)
- Financial tracking (subtotal, tax, discount, total)
"""

from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from apps.core.models import HubBaseModel


# =============================================================================
# Settings
# =============================================================================

class OrdersSettings(HubBaseModel):
    """Per-hub configuration for orders module."""

    # Kitchen display settings
    auto_print_tickets = models.BooleanField(default=True)
    show_prep_time = models.BooleanField(default=True)
    alert_threshold_minutes = models.PositiveIntegerField(default=15)

    # Order behavior
    use_rounds = models.BooleanField(default=True)
    auto_fire_on_round = models.BooleanField(default=False)
    default_order_type = models.CharField(max_length=20, default='dine_in')

    # Sound notifications
    sound_on_new_order = models.BooleanField(default=True)

    class Meta(HubBaseModel.Meta):
        db_table = 'orders_settings'
        verbose_name = _('Orders Settings')
        verbose_name_plural = _('Orders Settings')
        unique_together = [('hub_id',)]

    def __str__(self):
        return f"Orders Settings (Hub {self.hub_id})"

    @classmethod
    def get_settings(cls, hub_id):
        settings, _ = cls.all_objects.get_or_create(hub_id=hub_id)
        return settings


# =============================================================================
# Kitchen Stations
# =============================================================================

class KitchenStation(HubBaseModel):
    """
    Kitchen station for routing orders.
    Examples: Bar, Grill, Fryer, Dessert, Cold Kitchen.
    """
    name = models.CharField(max_length=100, verbose_name=_('Name'))
    name_es = models.CharField(max_length=100, blank=True, verbose_name=_('Name (Spanish)'))
    description = models.TextField(blank=True)

    # Visual
    color = models.CharField(max_length=7, default='#F97316')
    icon = models.CharField(max_length=50, default='flame-outline')

    # Printing
    printer_name = models.CharField(max_length=100, blank=True)

    # Display
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta(HubBaseModel.Meta):
        db_table = 'orders_kitchen_station'
        verbose_name = _('Kitchen Station')
        verbose_name_plural = _('Kitchen Stations')
        ordering = ['sort_order', 'name']
        unique_together = [('hub_id', 'name')]

    def __str__(self):
        return self.name

    @property
    def pending_count(self):
        return self.order_items.filter(
            status__in=['pending', 'preparing'],
            is_deleted=False,
        ).count()


# =============================================================================
# Orders
# =============================================================================

class Order(HubBaseModel):
    """Restaurant/retail order ticket."""

    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('preparing', _('Preparing')),
        ('ready', _('Ready')),
        ('served', _('Served')),
        ('paid', _('Paid')),
        ('cancelled', _('Cancelled')),
    ]

    ORDER_TYPE_CHOICES = [
        ('dine_in', _('Dine In')),
        ('takeaway', _('Takeaway')),
        ('delivery', _('Delivery')),
    ]

    PRIORITY_CHOICES = [
        ('normal', _('Normal')),
        ('rush', _('Rush')),
        ('vip', _('VIP')),
    ]

    # Identification
    order_number = models.CharField(max_length=50, db_index=True, verbose_name=_('Order Number'))

    # Links
    table = models.ForeignKey(
        'tables.Table',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='orders',
        verbose_name=_('Table'),
    )
    sale = models.ForeignKey(
        'sales.Sale',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='orders',
        verbose_name=_('Sale'),
    )
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='orders',
        verbose_name=_('Customer'),
    )
    waiter = models.ForeignKey(
        'accounts.LocalUser',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='waiter_orders',
        verbose_name=_('Waiter'),
    )

    # Order info
    order_type = models.CharField(
        max_length=20, choices=ORDER_TYPE_CHOICES,
        default='dine_in', verbose_name=_('Order Type'),
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='pending', verbose_name=_('Status'),
    )
    priority = models.CharField(
        max_length=20, choices=PRIORITY_CHOICES,
        default='normal', verbose_name=_('Priority'),
    )

    # Round/course
    round_number = models.PositiveIntegerField(default=1, verbose_name=_('Round Number'))

    # Notes
    notes = models.TextField(blank=True, default='')

    # Financial
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    # Timing
    fired_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Fired At'))
    ready_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Ready At'))
    served_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Served At'))

    class Meta(HubBaseModel.Meta):
        db_table = 'orders_order'
        verbose_name = _('Order')
        verbose_name_plural = _('Orders')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['hub_id', 'status']),
            models.Index(fields=['hub_id', 'created_at']),
            models.Index(fields=['hub_id', 'order_type']),
        ]

    def __str__(self):
        return f"Order #{self.order_number}"

    # ---- Properties ----

    @property
    def table_display(self):
        if self.table:
            return self.table.display_name
        return '-'

    @property
    def elapsed_minutes(self):
        if not self.fired_at:
            return 0
        delta = timezone.now() - self.fired_at
        return int(delta.total_seconds() / 60)

    @property
    def prep_time_minutes(self):
        if not self.fired_at or not self.ready_at:
            return None
        delta = self.ready_at - self.fired_at
        return int(delta.total_seconds() / 60)

    @property
    def is_delayed(self):
        settings = OrdersSettings.get_settings(self.hub_id)
        return (
            self.status in ['pending', 'preparing']
            and self.elapsed_minutes > settings.alert_threshold_minutes
        )

    @property
    def item_count(self):
        return self.items.filter(is_deleted=False).count()

    @property
    def pending_items_count(self):
        return self.items.filter(is_deleted=False, fired_at__isnull=True).count()

    @property
    def can_be_edited(self):
        return self.status in ['pending', 'preparing']

    # ---- Financial ----

    def calculate_totals(self):
        items = self.items.filter(is_deleted=False)
        self.subtotal = sum(item.total for item in items)
        self.total = self.subtotal - self.discount + self.tax
        return self.total

    # ---- Workflow ----

    def fire(self):
        """Send order to kitchen."""
        now = timezone.now()
        self.fired_at = now
        self.status = 'preparing'
        self.save(update_fields=['fired_at', 'status', 'updated_at'])

        self.items.filter(is_deleted=False, status='pending').update(
            status='preparing',
            fired_at=now,
        )
        return self

    def mark_ready(self):
        self.status = 'ready'
        self.ready_at = timezone.now()
        self.save(update_fields=['status', 'ready_at', 'updated_at'])
        return self

    def mark_served(self):
        self.status = 'served'
        self.served_at = timezone.now()
        self.save(update_fields=['status', 'served_at', 'updated_at'])
        return self

    def cancel(self, reason=''):
        self.status = 'cancelled'
        if reason:
            self.notes = f"{self.notes}\nCancelled: {reason}".strip()
        self.save(update_fields=['status', 'notes', 'updated_at'])
        self.items.filter(is_deleted=False).update(status='cancelled')
        return self

    def recall(self):
        """Recall a ready order back to preparing."""
        if self.status == 'ready':
            self.status = 'preparing'
            self.ready_at = None
            self.save(update_fields=['status', 'ready_at', 'updated_at'])
            self.items.filter(is_deleted=False, status='ready').update(
                status='preparing', completed_at=None,
            )
        return self

    # ---- Number generation ----

    @classmethod
    def generate_order_number(cls, hub_id):
        today = timezone.now()
        prefix = today.strftime('%Y%m%d')
        last = cls.all_objects.filter(
            hub_id=hub_id, order_number__startswith=prefix,
        ).order_by('-order_number').first()
        if last:
            try:
                num = int(last.order_number.split('-')[-1]) + 1
            except (ValueError, IndexError):
                num = 1
        else:
            num = 1
        return f"{prefix}-{num:04d}"


# =============================================================================
# Order Items
# =============================================================================

class OrderItem(HubBaseModel):
    """Individual item in an order, routed to a kitchen station."""

    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('preparing', _('Preparing')),
        ('ready', _('Ready')),
        ('served', _('Served')),
        ('cancelled', _('Cancelled')),
    ]

    order = models.ForeignKey(
        Order, on_delete=models.CASCADE,
        related_name='items', verbose_name=_('Order'),
    )
    station = models.ForeignKey(
        KitchenStation, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='order_items', verbose_name=_('Kitchen Station'),
    )
    product = models.ForeignKey(
        'inventory.Product', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='order_items', verbose_name=_('Product'),
    )

    # Snapshot
    product_name = models.CharField(max_length=255, verbose_name=_('Product Name'))
    unit_price = models.DecimalField(
        max_digits=10, decimal_places=2,
        default=Decimal('0.00'), verbose_name=_('Unit Price'),
    )

    # Quantity & total
    quantity = models.PositiveIntegerField(
        default=1, validators=[MinValueValidator(1)],
        verbose_name=_('Quantity'),
    )
    total = models.DecimalField(
        max_digits=10, decimal_places=2,
        default=Decimal('0.00'), verbose_name=_('Total'),
    )

    # Modifiers/notes
    modifiers = models.TextField(blank=True, verbose_name=_('Modifiers'))
    notes = models.TextField(blank=True, verbose_name=_('Special Instructions'))

    # Status
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='pending', verbose_name=_('Status'),
    )

    # Seat number (for splitting bills)
    seat_number = models.PositiveIntegerField(null=True, blank=True, verbose_name=_('Seat Number'))

    # Timing
    fired_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Sent to Kitchen'))
    started_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Started At'))
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Completed At'))

    class Meta(HubBaseModel.Meta):
        db_table = 'orders_order_item'
        verbose_name = _('Order Item')
        verbose_name_plural = _('Order Items')
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['station', 'status']),
        ]

    def __str__(self):
        return f"{self.quantity}x {self.product_name}"

    @property
    def display_name(self):
        if self.modifiers:
            return f"{self.product_name} ({self.modifiers})"
        return self.product_name

    @property
    def prep_time_minutes(self):
        if not self.started_at or not self.completed_at:
            return None
        return int((self.completed_at - self.started_at).total_seconds() / 60)

    def save(self, *args, **kwargs):
        self.total = self.unit_price * self.quantity
        if not self.product_name and self.product:
            self.product_name = self.product.name
        if not self.unit_price and self.product:
            self.unit_price = getattr(self.product, 'price', Decimal('0.00'))
            self.total = self.unit_price * self.quantity
        super().save(*args, **kwargs)

    def start_preparing(self):
        self.status = 'preparing'
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at', 'updated_at'])
        return self

    def mark_ready(self):
        self.status = 'ready'
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_at', 'updated_at'])

        # Check if all items in order are ready
        pending = self.order.items.filter(is_deleted=False).exclude(
            status__in=['ready', 'served', 'cancelled'],
        ).exists()
        if not pending:
            self.order.mark_ready()
        return self

    def cancel(self):
        self.status = 'cancelled'
        self.save(update_fields=['status', 'updated_at'])
        return self


# =============================================================================
# Order Modifier
# =============================================================================

class OrderModifier(HubBaseModel):
    """Modifier applied to an order item (extra toppings, cooking preferences)."""

    order_item = models.ForeignKey(
        OrderItem, on_delete=models.CASCADE,
        related_name='modifier_details', verbose_name=_('Order Item'),
    )
    name = models.CharField(max_length=100, verbose_name=_('Name'))
    price = models.DecimalField(
        max_digits=10, decimal_places=2,
        default=Decimal('0.00'), verbose_name=_('Price'),
    )

    class Meta(HubBaseModel.Meta):
        db_table = 'orders_order_modifier'
        verbose_name = _('Order Modifier')
        verbose_name_plural = _('Order Modifiers')

    def __str__(self):
        if self.price > 0:
            return f"{self.name} (+{self.price})"
        return self.name


# =============================================================================
# Station Routing
# =============================================================================

class ProductStation(HubBaseModel):
    """Maps a product to a kitchen station for automatic routing."""

    product = models.ForeignKey(
        'inventory.Product', on_delete=models.CASCADE,
        related_name='station_mappings', verbose_name=_('Product'),
    )
    station = models.ForeignKey(
        KitchenStation, on_delete=models.CASCADE,
        related_name='product_mappings', verbose_name=_('Kitchen Station'),
    )

    class Meta(HubBaseModel.Meta):
        db_table = 'orders_product_station'
        verbose_name = _('Product Station Mapping')
        verbose_name_plural = _('Product Station Mappings')
        unique_together = [('hub_id', 'product')]

    def __str__(self):
        return f"{self.product} -> {self.station.name}"

    @classmethod
    def get_station_for_product(cls, hub_id, product_id):
        try:
            return cls.objects.select_related('station').get(
                hub_id=hub_id, product_id=product_id,
                station__is_active=True, is_deleted=False,
            ).station
        except cls.DoesNotExist:
            return None


class CategoryStation(HubBaseModel):
    """Maps a product category to a kitchen station for automatic routing."""

    category = models.ForeignKey(
        'inventory.Category', on_delete=models.CASCADE,
        related_name='station_mappings', verbose_name=_('Category'),
    )
    station = models.ForeignKey(
        KitchenStation, on_delete=models.CASCADE,
        related_name='category_mappings', verbose_name=_('Kitchen Station'),
    )

    class Meta(HubBaseModel.Meta):
        db_table = 'orders_category_station'
        verbose_name = _('Category Station Mapping')
        verbose_name_plural = _('Category Station Mappings')
        unique_together = [('hub_id', 'category')]

    def __str__(self):
        return f"{self.category} -> {self.station.name}"

    @classmethod
    def get_station_for_category(cls, hub_id, category_id):
        try:
            return cls.objects.select_related('station').get(
                hub_id=hub_id, category_id=category_id,
                station__is_active=True, is_deleted=False,
            ).station
        except cls.DoesNotExist:
            return None


def get_station_for_product(hub_id, product_id):
    """
    Resolve the kitchen station for a product.
    Priority: direct product mapping > category mapping > None.
    """
    station = ProductStation.get_station_for_product(hub_id, product_id)
    if station:
        return station

    try:
        from inventory.models import Product
        product = Product.objects.get(pk=product_id)
        if product.category_id:
            station = CategoryStation.get_station_for_category(hub_id, product.category_id)
            if station:
                return station
    except Exception:
        pass

    return None
