"""
Orders Module Configuration

This file defines the module metadata and navigation for the Orders module.
Order management with kitchen display system (KDS) integration.
Used by the @module_view decorator to automatically render navigation tabs.
"""
from django.utils.translation import gettext_lazy as _

# Module Identification
MODULE_ID = "orders"
MODULE_NAME = _("Orders")
MODULE_ICON = "receipt-outline"
MODULE_VERSION = "1.0.0"
MODULE_CATEGORY = "horeca"  # Changed from "restaurant" to valid category

# Target Industries (business verticals this module is designed for)
MODULE_INDUSTRIES = [
    "restaurant", # Restaurants
    "bar",        # Bars & pubs
    "cafe",       # Cafes & bakeries
    "fast_food",  # Fast food
    "catering",   # Catering & events
]

# Sidebar Menu Configuration
MENU = {
    "label": _("Orders"),
    "icon": "receipt-outline",
    "order": 45,
    "show": True,
}

# Internal Navigation (Tabs)
NAVIGATION = [
    {
        "id": "orders",
        "label": _("Orders"),
        "icon": "receipt-outline",
        "view": "",
    },
    {
        "id": "kds",
        "label": _("Kitchen"),
        "icon": "tv-outline",
        "view": "kds",
    },
    {
        "id": "stations",
        "label": _("Stations"),
        "icon": "flame-outline",
        "view": "stations",
    },
    {
        "id": "routing",
        "label": _("Routing"),
        "icon": "git-branch-outline",
        "view": "routing",
    },
    {
        "id": "settings",
        "label": _("Settings"),
        "icon": "settings-outline",
        "view": "settings",
    },
]

# Module Dependencies
DEPENDENCIES = ["sales>=1.0.0"]

# Default Settings
SETTINGS = {
    "auto_fire_enabled": False,
    "sound_notifications": True,
    "ticket_printing": True,
    "order_timeout_minutes": 30,
}

# Permissions
PERMISSIONS = [
    "orders.view_order",
    "orders.add_order",
    "orders.change_order",
    "orders.delete_order",
    "orders.fire_order",
    "orders.bump_order",
    "orders.cancel_order",
    "orders.manage_stations",
    "orders.manage_routing",
]
