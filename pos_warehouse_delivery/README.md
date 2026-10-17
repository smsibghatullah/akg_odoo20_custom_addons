# POS Warehouse Delivery Orders (pos_warehouse_delivery)
**Odoo 20 version** (migrated from Odoo 16)

## Features
- Har POS orderline par **Warehouse dropdown** (selected line par), baaqi lines par one-line summary
- **Ship Later** checkbox + **Ship Date** (POS config mein "Allow Ship Later" ON ho to)
- Order paid hone par **warehouse-wise alag delivery orders** (ship-later wali lines ka alag, open delivery order scheduled date ke sath)
- Refund lines apni original line ki warehouse se return hoti hain

## Configuration
Point of Sale -> Configuration -> Point of Sale -> (shop) -> Configuration tab:
1. **Warehouse-wise Delivery Orders** ON + **Default Warehouse**
2. **Allow Ship Later** ON (optional)

## Technical notes (Odoo 20)
- Depends on `pos_stock` (delivery pickings / `stock.picking.pos_order_id` core mein hain)
- `stock.warehouse` POS mein load hota hai (`pos.load.mixin`)
- `pos.order.line` fields: `warehouse_id`, `ship_later`, `ship_later_date` (`_load_pos_data_fields` mein add)
- Frontend: `patch(Orderline)` + template extension of `point_of_sale.Orderline`, `patch(PosStore)` for default warehouse
- Assets bundle: `point_of_sale._assets_pos`
