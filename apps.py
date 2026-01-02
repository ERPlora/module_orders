from django.apps import AppConfig


class OrdersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'orders'
    verbose_name = 'Orders & Kitchen Display'

    def ready(self):
        try:
            from . import signals  # noqa
        except ImportError:
            pass
