"""AI tools for the Orders module."""
from assistant.tools import AssistantTool, register_tool


@register_tool
class ListOrders(AssistantTool):
    name = "list_orders"
    description = "List orders with filters. Returns order_number, status, priority, table, item_count, elapsed time."
    module_id = "orders"
    required_permission = "orders.view_order"
    parameters = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "description": "Filter: pending, preparing, ready, served, paid, cancelled"},
            "order_type": {"type": "string", "description": "Filter: dine_in, takeaway, delivery"},
            "priority": {"type": "string", "description": "Filter: normal, rush, vip"},
            "table_id": {"type": "string", "description": "Filter by table ID"},
            "limit": {"type": "integer", "description": "Max results (default 20)"},
        },
        "required": [],
        "additionalProperties": False,
    }

    def execute(self, args, request):
        from orders.models import Order
        qs = Order.objects.select_related('table', 'waiter').all()
        if args.get('status'):
            qs = qs.filter(status=args['status'])
        if args.get('order_type'):
            qs = qs.filter(order_type=args['order_type'])
        if args.get('priority'):
            qs = qs.filter(priority=args['priority'])
        if args.get('table_id'):
            qs = qs.filter(table_id=args['table_id'])
        limit = args.get('limit', 20)
        orders = qs.order_by('-created_at')[:limit]
        return {
            "orders": [
                {
                    "id": str(o.id),
                    "order_number": o.order_number,
                    "status": o.status,
                    "order_type": o.order_type,
                    "priority": o.priority,
                    "table": o.table.number if o.table else None,
                    "waiter": o.waiter.display_name if o.waiter else None,
                    "item_count": o.item_count,
                    "total": str(o.total),
                    "elapsed_minutes": o.elapsed_minutes,
                    "is_delayed": o.is_delayed,
                }
                for o in orders
            ],
            "total": qs.count(),
        }


@register_tool
class GetOrder(AssistantTool):
    name = "get_order"
    description = "Get full order details including items, modifiers, timing, and financials."
    module_id = "orders"
    required_permission = "orders.view_order"
    parameters = {
        "type": "object",
        "properties": {
            "order_id": {"type": "string", "description": "Order ID"},
            "order_number": {"type": "string", "description": "Order number (e.g., '20260301-0001')"},
        },
        "required": [],
        "additionalProperties": False,
    }

    def execute(self, args, request):
        from orders.models import Order
        if args.get('order_id'):
            o = Order.objects.get(id=args['order_id'])
        elif args.get('order_number'):
            o = Order.objects.get(order_number=args['order_number'])
        else:
            return {"error": "Provide order_id or order_number"}
        items = o.items.select_related('station', 'product').all()
        return {
            "id": str(o.id),
            "order_number": o.order_number,
            "status": o.status,
            "order_type": o.order_type,
            "priority": o.priority,
            "table": o.table.number if o.table else None,
            "waiter": o.waiter.display_name if o.waiter else None,
            "notes": o.notes,
            "subtotal": str(o.subtotal),
            "tax": str(o.tax),
            "discount": str(o.discount),
            "total": str(o.total),
            "elapsed_minutes": o.elapsed_minutes,
            "items": [
                {
                    "id": str(i.id),
                    "product_name": i.product_name,
                    "quantity": i.quantity,
                    "unit_price": str(i.unit_price),
                    "total": str(i.total),
                    "status": i.status,
                    "station": i.station.name if i.station else None,
                    "notes": i.notes,
                    "modifiers": i.modifiers,
                    "seat_number": i.seat_number,
                }
                for i in items
            ],
        }


@register_tool
class CreateOrder(AssistantTool):
    name = "create_order"
    description = "Create a new order with items. For restaurant setup, creates dine-in/takeaway/delivery orders."
    module_id = "orders"
    required_permission = "orders.add_order"
    requires_confirmation = True
    parameters = {
        "type": "object",
        "properties": {
            "order_type": {"type": "string", "description": "Type: dine_in, takeaway, delivery (default dine_in)"},
            "table_id": {"type": "string", "description": "Table ID (for dine_in)"},
            "customer_id": {"type": "string", "description": "Customer ID"},
            "waiter_id": {"type": "string", "description": "Waiter user ID"},
            "priority": {"type": "string", "description": "Priority: normal, rush, vip (default normal)"},
            "notes": {"type": "string", "description": "Order notes"},
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "product_id": {"type": "string", "description": "Product ID"},
                        "quantity": {"type": "integer", "description": "Quantity"},
                        "notes": {"type": "string", "description": "Item notes"},
                        "modifiers": {"type": "string", "description": "Modifiers text"},
                    },
                    "required": ["product_id", "quantity"],
                },
                "description": "Order items",
            },
        },
        "required": ["order_type"],
        "additionalProperties": False,
    }

    def execute(self, args, request):
        from orders.models import Order, OrderItem
        from inventory.models import Product
        o = Order.objects.create(
            order_type=args['order_type'],
            table_id=args.get('table_id'),
            customer_id=args.get('customer_id'),
            waiter_id=args.get('waiter_id'),
            priority=args.get('priority', 'normal'),
            notes=args.get('notes', ''),
        )
        items_created = []
        for item_data in args.get('items', []):
            product = Product.objects.get(id=item_data['product_id'])
            oi = OrderItem.objects.create(
                order=o,
                product=product,
                product_name=product.name,
                unit_price=product.price,
                quantity=item_data['quantity'],
                total=product.price * item_data['quantity'],
                notes=item_data.get('notes', ''),
                modifiers=item_data.get('modifiers', ''),
            )
            items_created.append({"product": product.name, "quantity": oi.quantity})
        # Update order totals
        o.subtotal = sum(i.total for i in o.items.all())
        o.total = o.subtotal + o.tax - o.discount
        o.save(update_fields=['subtotal', 'total'])
        return {
            "id": str(o.id),
            "order_number": o.order_number,
            "items": items_created,
            "total": str(o.total),
            "created": True,
        }


@register_tool
class UpdateOrderStatus(AssistantTool):
    name = "update_order_status"
    description = "Update an order's status: fire (send to kitchen), mark_ready, mark_served, cancel."
    module_id = "orders"
    required_permission = "orders.change_order"
    requires_confirmation = True
    parameters = {
        "type": "object",
        "properties": {
            "order_id": {"type": "string", "description": "Order ID"},
            "action": {"type": "string", "description": "Action: fire, mark_ready, mark_served, cancel, recall"},
            "reason": {"type": "string", "description": "Cancel reason (required for cancel)"},
        },
        "required": ["order_id", "action"],
        "additionalProperties": False,
    }

    def execute(self, args, request):
        from orders.models import Order
        o = Order.objects.get(id=args['order_id'])
        action = args['action']
        if action == 'fire':
            o.fire()
        elif action == 'mark_ready':
            o.mark_ready()
        elif action == 'mark_served':
            o.mark_served()
        elif action == 'cancel':
            o.cancel(args.get('reason', ''))
        elif action == 'recall':
            o.recall()
        else:
            return {"error": f"Unknown action: {action}"}
        return {"id": str(o.id), "order_number": o.order_number, "status": o.status, "updated": True}


@register_tool
class ListKitchenStations(AssistantTool):
    name = "list_kitchen_stations"
    description = "List kitchen stations (e.g., 'Plancha', 'Fríos', 'Bebidas'). Shows name, color, pending orders."
    module_id = "orders"
    required_permission = "orders.view_order"
    parameters = {
        "type": "object",
        "properties": {
            "is_active": {"type": "boolean", "description": "Filter by active status"},
        },
        "required": [],
        "additionalProperties": False,
    }

    def execute(self, args, request):
        from orders.models import KitchenStation
        qs = KitchenStation.objects.all()
        if 'is_active' in args:
            qs = qs.filter(is_active=args['is_active'])
        return {
            "stations": [
                {
                    "id": str(s.id),
                    "name": s.name,
                    "color": s.color,
                    "icon": s.icon,
                    "printer_name": s.printer_name,
                    "is_active": s.is_active,
                    "pending_count": s.pending_count,
                }
                for s in qs
            ]
        }


@register_tool
class CreateKitchenStation(AssistantTool):
    name = "create_kitchen_station"
    description = "Create a kitchen station for order routing (e.g., 'Plancha', 'Horno', 'Barra')."
    module_id = "orders"
    required_permission = "orders.manage_settings"
    requires_confirmation = True
    parameters = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Station name"},
            "color": {"type": "string", "description": "Hex color (e.g., '#FF5733')"},
            "icon": {"type": "string", "description": "Icon name (djicons)"},
            "printer_name": {"type": "string", "description": "Printer name for this station"},
        },
        "required": ["name"],
        "additionalProperties": False,
    }

    def execute(self, args, request):
        from orders.models import KitchenStation
        s = KitchenStation.objects.create(
            name=args['name'],
            color=args.get('color', ''),
            icon=args.get('icon', ''),
            printer_name=args.get('printer_name', ''),
        )
        return {"id": str(s.id), "name": s.name, "created": True}


@register_tool
class SetStationRouting(AssistantTool):
    name = "set_station_routing"
    description = "Route a product or category to a kitchen station. Product routes take priority over category routes."
    module_id = "orders"
    required_permission = "orders.manage_settings"
    requires_confirmation = True
    parameters = {
        "type": "object",
        "properties": {
            "station_id": {"type": "string", "description": "Kitchen station ID"},
            "product_id": {"type": "string", "description": "Product ID (for product-level routing)"},
            "category_id": {"type": "string", "description": "Category ID (for category-level routing)"},
        },
        "required": ["station_id"],
        "additionalProperties": False,
    }

    def execute(self, args, request):
        from orders.models import ProductStation, CategoryStation
        station_id = args['station_id']
        result = {}
        if args.get('product_id'):
            ps, created = ProductStation.objects.update_or_create(
                product_id=args['product_id'],
                defaults={'station_id': station_id},
            )
            result['product_routing'] = {"product_id": args['product_id'], "created": created}
        if args.get('category_id'):
            cs, created = CategoryStation.objects.update_or_create(
                category_id=args['category_id'],
                defaults={'station_id': station_id},
            )
            result['category_routing'] = {"category_id": args['category_id'], "created": created}
        return result


@register_tool
class GetOrdersSettings(AssistantTool):
    name = "get_orders_settings"
    description = "Get orders module settings (auto_print, prep time alerts, rounds, default order type)."
    module_id = "orders"
    required_permission = "orders.view_settings"
    parameters = {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    }

    def execute(self, args, request):
        from orders.models import OrdersSettings
        s = OrdersSettings.get_settings()
        return {
            "auto_print_tickets": s.auto_print_tickets,
            "show_prep_time": s.show_prep_time,
            "alert_threshold_minutes": s.alert_threshold_minutes,
            "use_rounds": s.use_rounds,
            "auto_fire_on_round": s.auto_fire_on_round,
            "default_order_type": s.default_order_type,
            "sound_on_new_order": s.sound_on_new_order,
        }


@register_tool
class UpdateOrdersSettings(AssistantTool):
    name = "update_orders_settings"
    description = "Update orders module settings."
    module_id = "orders"
    required_permission = "orders.change_settings"
    requires_confirmation = True
    parameters = {
        "type": "object",
        "properties": {
            "auto_print_tickets": {"type": "boolean"},
            "show_prep_time": {"type": "boolean"},
            "alert_threshold_minutes": {"type": "integer"},
            "use_rounds": {"type": "boolean"},
            "auto_fire_on_round": {"type": "boolean"},
            "default_order_type": {"type": "string", "description": "dine_in, takeaway, delivery"},
            "sound_on_new_order": {"type": "boolean"},
        },
        "required": [],
        "additionalProperties": False,
    }

    def execute(self, args, request):
        from orders.models import OrdersSettings
        s = OrdersSettings.get_settings()
        updated = []
        for field in ['auto_print_tickets', 'show_prep_time', 'alert_threshold_minutes',
                       'use_rounds', 'auto_fire_on_round', 'default_order_type', 'sound_on_new_order']:
            if field in args:
                setattr(s, field, args[field])
                updated.append(field)
        if updated:
            s.save()
        return {"updated_fields": updated, "success": True}
