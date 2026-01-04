from django.apps import AppConfig


class OrdersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "orders"
    verbose_name = "Orders"

    def ready(self):
        pass

    @staticmethod
    def do_after_order_create(order) -> None:
        """Called after order is created."""
        pass

    @staticmethod
    def do_after_order_update(order) -> None:
        """Called after order is updated."""
        pass

    @staticmethod
    def do_after_order_complete(order) -> None:
        """Called after order is completed."""
        pass

    @staticmethod
    def do_after_order_cancel(order) -> None:
        """Called after order is cancelled."""
        pass

    @staticmethod
    def filter_orders_list(queryset, request):
        """Filter orders queryset."""
        return queryset
