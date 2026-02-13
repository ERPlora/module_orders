"""
Orders Module Configuration

Order management for restaurants, bars and cafes.
"""
from django.utils.translation import gettext_lazy as _

MODULE_ID = "orders"
MODULE_NAME = _("Orders")
MODULE_ICON = "clipboard-outline"
MODULE_VERSION = "1.0.0"
MODULE_CATEGORY = "pos"

MODULE_INDUSTRIES = ["restaurant", "bar", "cafe", "fast_food", "catering"]

MENU = {
    "label": _("Orders"),
    "icon": "clipboard-outline",
    "order": 45,
    "show": True,
}

NAVIGATION = [
    {"id": "dashboard", "label": _("Overview"), "icon": "grid-outline", "view": ""},
    {"id": "active", "label": _("Active"), "icon": "time-outline", "view": "active"},
    {"id": "history", "label": _("History"), "icon": "archive-outline", "view": "history"},
    {"id": "settings", "label": _("Settings"), "icon": "settings-outline", "view": "settings"},
]

DEPENDENCIES = ['tables', 'sales', 'customers', 'inventory']

SETTINGS = {
    "auto_accept_orders": True,
    "default_prep_time": 15,
    "notify_kitchen": True,
}

PERMISSIONS = [
    ("view_order", _("Can view orders")),
    ("add_order", _("Can add orders")),
    ("change_order", _("Can change orders")),
    ("delete_order", _("Can delete orders")),
    ("cancel_order", _("Can cancel orders")),
    ("complete_order", _("Can complete orders")),
    ("view_history", _("Can view order history")),
    ("view_settings", _("Can view settings")),
    ("change_settings", _("Can change settings")),
]

ROLE_PERMISSIONS = {
    "admin": ["*"],
    "manager": [
        "view_order", "add_order", "change_order", "delete_order",
        "cancel_order", "complete_order", "view_history", "view_settings",
    ],
    "employee": ["view_order", "add_order", "complete_order"],
}
