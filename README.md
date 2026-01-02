# Orders Module

Order management with Kitchen Display System (KDS) integration for restaurants and food service.

## Features

- Order creation and management
- Kitchen ticket routing
- Station-based order routing
- Order status tracking
- Order history and search
- Integration with Sales and Kitchen modules

## Installation

This module is installed automatically when activated in ERPlora Hub.

### Dependencies

- ERPlora Hub >= 1.0.0
- Required: `sales` >= 1.0.0
- Optional: `kitchen` for KDS integration

## Configuration

Access module settings at `/m/orders/settings/`.

### Available Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `auto_fire_enabled` | boolean | `false` | Auto-fire orders to kitchen |
| `sound_notifications` | boolean | `true` | Play notification sounds |
| `ticket_printing` | boolean | `true` | Enable ticket printing |
| `order_timeout_minutes` | integer | `30` | Order timeout in minutes |

## Usage

### Views

| View | URL | Description |
|------|-----|-------------|
| Orders | `/m/orders/` | Order list |
| Kitchen | `/m/orders/kds/` | KDS view |
| Stations | `/m/orders/stations/` | Station management |
| Routing | `/m/orders/routing/` | Order routing rules |
| Settings | `/m/orders/settings/` | Module configuration |

## Permissions

| Permission | Description |
|------------|-------------|
| `orders.view_order` | View orders |
| `orders.add_order` | Create orders |
| `orders.change_order` | Edit orders |
| `orders.delete_order` | Delete orders |
| `orders.fire_order` | Fire orders to kitchen |
| `orders.bump_order` | Bump completed orders |
| `orders.cancel_order` | Cancel orders |
| `orders.manage_stations` | Manage stations |
| `orders.manage_routing` | Manage routing rules |

## Module Icon

Location: `static/icons/icon.svg`

Icon source: [React Icons - Ionicons 5](https://react-icons.github.io/react-icons/icons/io5/)

---

**Version:** 1.0.0
**Category:** restaurant
**Author:** ERPlora Team
