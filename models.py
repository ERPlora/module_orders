"""
Orders Module Models

Provides order/ticket management for hospitality businesses.
Features:
- Order tickets with multiple items
- Kitchen display system (KDS)
- Order routing to different stations
- Preparation time tracking
- Rounds/courses support
"""

from django.db import models
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from decimal import Decimal


class OrdersConfig(models.Model):
    """
    Singleton configuration for orders module.
    """
    # Kitchen display settings
    auto_print_tickets = models.BooleanField(
        default=True,
        verbose_name=_("Auto Print Kitchen Tickets"),
        help_text=_("Automatically print tickets when order is placed")
    )
    show_prep_time = models.BooleanField(
        default=True,
        verbose_name=_("Show Preparation Time"),
        help_text=_("Display elapsed preparation time on kitchen display")
    )
    alert_threshold_minutes = models.PositiveIntegerField(
        default=15,
        verbose_name=_("Alert Threshold (minutes)"),
        help_text=_("Time before order is flagged as delayed")
    )

    # Order behavior
    use_rounds = models.BooleanField(
        default=True,
        verbose_name=_("Use Rounds/Courses"),
        help_text=_("Allow grouping items into rounds (starter, main, dessert)")
    )
    auto_fire_on_round = models.BooleanField(
        default=False,
        verbose_name=_("Auto Fire Rounds"),
        help_text=_("Automatically send rounds to kitchen when created")
    )

    # Sound notifications
    sound_on_new_order = models.BooleanField(
        default=True,
        verbose_name=_("Sound on New Order"),
        help_text=_("Play sound when new order arrives")
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'orders'
        db_table = 'orders_config'
        verbose_name = _("Orders Configuration")
        verbose_name_plural = _("Orders Configuration")

    def __str__(self):
        return "Orders Configuration"

    @classmethod
    def get_config(cls):
        """Get or create singleton config."""
        config, _ = cls.objects.get_or_create(pk=1)
        return config

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)


class KitchenStation(models.Model):
    """
    Represents a kitchen station/printer for routing orders.

    Examples: Bar, Grill, Fryer, Dessert, Cold Kitchen
    """
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_("Name")
    )
    name_es = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("Name (Spanish)")
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Description")
    )

    # Visual
    color = models.CharField(
        max_length=7,
        default="#F97316",
        verbose_name=_("Color")
    )
    icon = models.CharField(
        max_length=50,
        default="flame-outline",
        verbose_name=_("Icon")
    )

    # Printing
    printer_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("Printer Name"),
        help_text=_("System printer name for this station")
    )

    # Display order
    order = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Display Order")
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Active")
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'orders'
        db_table = 'orders_kitchen_station'
        verbose_name = _("Kitchen Station")
        verbose_name_plural = _("Kitchen Stations")
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    @property
    def pending_count(self):
        """Number of pending items for this station."""
        return self.items.filter(
            status__in=[OrderItem.STATUS_PENDING, OrderItem.STATUS_PREPARING]
        ).count()


class Order(models.Model):
    """
    Represents a kitchen order/ticket.

    Can be linked to a table and/or sale.
    """
    # Status choices
    STATUS_PENDING = 'pending'
    STATUS_PREPARING = 'preparing'
    STATUS_READY = 'ready'
    STATUS_SERVED = 'served'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_PENDING, _('Pending')),
        (STATUS_PREPARING, _('Preparing')),
        (STATUS_READY, _('Ready')),
        (STATUS_SERVED, _('Served')),
        (STATUS_CANCELLED, _('Cancelled')),
    ]

    # Priority choices
    PRIORITY_NORMAL = 'normal'
    PRIORITY_RUSH = 'rush'
    PRIORITY_VIP = 'vip'

    PRIORITY_CHOICES = [
        (PRIORITY_NORMAL, _('Normal')),
        (PRIORITY_RUSH, _('Rush')),
        (PRIORITY_VIP, _('VIP')),
    ]

    # Order number
    order_number = models.CharField(
        max_length=20,
        unique=True,
        verbose_name=_("Order Number")
    )

    # Links to other modules (using IDs to avoid circular imports)
    table_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Table ID"),
        help_text=_("ID of the table from tables module")
    )
    sale_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Sale ID"),
        help_text=_("ID of the sale from sales module")
    )

    # Order info
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        verbose_name=_("Status")
    )
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default=PRIORITY_NORMAL,
        verbose_name=_("Priority")
    )

    # Round/course
    round_number = models.PositiveIntegerField(
        default=1,
        verbose_name=_("Round Number"),
        help_text=_("Course number (1=starter, 2=main, etc.)")
    )

    # Staff
    created_by = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("Created By"),
        help_text=_("Name of the waiter who placed the order")
    )

    # Notes
    notes = models.TextField(
        blank=True,
        verbose_name=_("Notes")
    )

    # Timing
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    fired_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Fired At"),
        help_text=_("When order was sent to kitchen")
    )
    ready_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Ready At")
    )
    served_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Served At")
    )

    class Meta:
        app_label = 'orders'
        db_table = 'orders_order'
        verbose_name = _("Order")
        verbose_name_plural = _("Orders")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['table_id']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Order #{self.order_number}"

    @property
    def table_display(self):
        """Get table number for display."""
        if self.table_id:
            try:
                from tables.models import Table
                table = Table.objects.get(pk=self.table_id)
                return table.number
            except Exception:
                pass
        return "-"

    @property
    def elapsed_minutes(self):
        """Get elapsed time since order was fired."""
        if not self.fired_at:
            return 0
        delta = timezone.now() - self.fired_at
        return int(delta.total_seconds() / 60)

    @property
    def prep_time_minutes(self):
        """Get actual preparation time in minutes."""
        if not self.fired_at or not self.ready_at:
            return None
        delta = self.ready_at - self.fired_at
        return int(delta.total_seconds() / 60)

    @property
    def is_delayed(self):
        """Check if order is taking too long."""
        config = OrdersConfig.get_config()
        return (
            self.status in [self.STATUS_PENDING, self.STATUS_PREPARING] and
            self.elapsed_minutes > config.alert_threshold_minutes
        )

    @property
    def item_count(self):
        """Number of items in this order."""
        return self.items.count()

    def fire(self):
        """Send order to kitchen."""
        self.fired_at = timezone.now()
        self.status = self.STATUS_PREPARING
        self.save()

        # Fire all pending items
        self.items.filter(status=OrderItem.STATUS_PENDING).update(
            status=OrderItem.STATUS_PREPARING,
            started_at=timezone.now()
        )

        return self

    def mark_ready(self):
        """Mark order as ready for pickup/service."""
        self.status = self.STATUS_READY
        self.ready_at = timezone.now()
        self.save()
        return self

    def mark_served(self):
        """Mark order as served to customer."""
        self.status = self.STATUS_SERVED
        self.served_at = timezone.now()
        self.save()
        return self

    def cancel(self, reason=''):
        """Cancel the order."""
        self.status = self.STATUS_CANCELLED
        if reason:
            self.notes = f"{self.notes}\nCancelled: {reason}".strip()
        self.save()

        # Cancel all items
        self.items.update(status=OrderItem.STATUS_CANCELLED)

        return self

    @classmethod
    def generate_order_number(cls):
        """Generate a unique order number."""
        from django.utils import timezone
        import random
        date_part = timezone.now().strftime('%y%m%d')
        random_part = random.randint(1000, 9999)
        return f"{date_part}-{random_part}"

    @classmethod
    def create_order(cls, table_id=None, sale_id=None, created_by='', round_number=1, notes=''):
        """Create a new order with auto-generated number."""
        return cls.objects.create(
            order_number=cls.generate_order_number(),
            table_id=table_id,
            sale_id=sale_id,
            created_by=created_by,
            round_number=round_number,
            notes=notes
        )


class OrderItem(models.Model):
    """
    Individual item in an order.

    Routed to a specific kitchen station.
    """
    # Status choices
    STATUS_PENDING = 'pending'
    STATUS_PREPARING = 'preparing'
    STATUS_READY = 'ready'
    STATUS_SERVED = 'served'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_PENDING, _('Pending')),
        (STATUS_PREPARING, _('Preparing')),
        (STATUS_READY, _('Ready')),
        (STATUS_SERVED, _('Served')),
        (STATUS_CANCELLED, _('Cancelled')),
    ]

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_("Order")
    )

    station = models.ForeignKey(
        KitchenStation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='items',
        verbose_name=_("Kitchen Station")
    )

    # Product info (using ID to avoid circular imports)
    product_id = models.PositiveIntegerField(
        verbose_name=_("Product ID")
    )
    product_name = models.CharField(
        max_length=255,
        verbose_name=_("Product Name")
    )

    # Quantity
    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        verbose_name=_("Quantity")
    )

    # Modifiers/notes
    modifiers = models.TextField(
        blank=True,
        verbose_name=_("Modifiers"),
        help_text=_("Applied modifiers (e.g., 'No onions, Extra cheese')")
    )
    notes = models.TextField(
        blank=True,
        verbose_name=_("Special Instructions")
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        verbose_name=_("Status")
    )

    # Seat number (for splitting bills)
    seat_number = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Seat Number")
    )

    # Timing
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Started At")
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Completed At")
    )

    class Meta:
        app_label = 'orders'
        db_table = 'orders_order_item'
        verbose_name = _("Order Item")
        verbose_name_plural = _("Order Items")
        ordering = ['order', 'created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['station', 'status']),
        ]

    def __str__(self):
        return f"{self.quantity}x {self.product_name}"

    @property
    def display_name(self):
        """Get display name with modifiers."""
        if self.modifiers:
            return f"{self.product_name} ({self.modifiers})"
        return self.product_name

    @property
    def prep_time_minutes(self):
        """Get preparation time in minutes."""
        if not self.started_at or not self.completed_at:
            return None
        delta = self.completed_at - self.started_at
        return int(delta.total_seconds() / 60)

    def start_preparing(self):
        """Mark item as being prepared."""
        self.status = self.STATUS_PREPARING
        self.started_at = timezone.now()
        self.save()
        return self

    def mark_ready(self):
        """Mark item as ready."""
        self.status = self.STATUS_READY
        self.completed_at = timezone.now()
        self.save()

        # Check if all items in order are ready
        order = self.order
        pending = order.items.exclude(
            status__in=[self.STATUS_READY, self.STATUS_SERVED, self.STATUS_CANCELLED]
        ).exists()

        if not pending:
            order.mark_ready()

        return self

    def cancel(self):
        """Cancel this item."""
        self.status = self.STATUS_CANCELLED
        self.save()
        return self

    @classmethod
    def add_to_order(cls, order, product_id, product_name, quantity=1,
                     station=None, modifiers='', notes='', seat_number=None):
        """Add an item to an order."""
        return cls.objects.create(
            order=order,
            product_id=product_id,
            product_name=product_name,
            quantity=quantity,
            station=station,
            modifiers=modifiers,
            notes=notes,
            seat_number=seat_number
        )


class ProductStation(models.Model):
    """
    Maps products to kitchen stations for automatic routing.
    """
    product_id = models.PositiveIntegerField(
        unique=True,
        verbose_name=_("Product ID")
    )
    station = models.ForeignKey(
        KitchenStation,
        on_delete=models.CASCADE,
        related_name='products',
        verbose_name=_("Kitchen Station")
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'orders'
        db_table = 'orders_product_station'
        verbose_name = _("Product Station Mapping")
        verbose_name_plural = _("Product Station Mappings")

    def __str__(self):
        return f"Product {self.product_id} -> {self.station.name}"

    @classmethod
    def get_station_for_product(cls, product_id):
        """Get the kitchen station for a product."""
        try:
            mapping = cls.objects.select_related('station').get(
                product_id=product_id,
                station__is_active=True
            )
            return mapping.station
        except cls.DoesNotExist:
            return None


class CategoryStation(models.Model):
    """
    Maps categories to kitchen stations for automatic routing.
    Products inherit station from category if not explicitly set.
    """
    category_id = models.PositiveIntegerField(
        unique=True,
        verbose_name=_("Category ID")
    )
    station = models.ForeignKey(
        KitchenStation,
        on_delete=models.CASCADE,
        related_name='categories',
        verbose_name=_("Kitchen Station")
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'orders'
        db_table = 'orders_category_station'
        verbose_name = _("Category Station Mapping")
        verbose_name_plural = _("Category Station Mappings")

    def __str__(self):
        return f"Category {self.category_id} -> {self.station.name}"

    @classmethod
    def get_station_for_category(cls, category_id):
        """Get the kitchen station for a category."""
        try:
            mapping = cls.objects.select_related('station').get(
                category_id=category_id,
                station__is_active=True
            )
            return mapping.station
        except cls.DoesNotExist:
            return None
