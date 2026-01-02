"""
Orders Module Signals

Handles integration with sales and tables modules.
"""

import logging
from django.dispatch import Signal

logger = logging.getLogger(__name__)

# Signals this module emits
order_created = Signal()  # Provides: order
order_fired = Signal()  # Provides: order
order_ready = Signal()  # Provides: order
order_served = Signal()  # Provides: order
order_cancelled = Signal()  # Provides: order, reason
