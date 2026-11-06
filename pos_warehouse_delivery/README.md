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

## v20.0.1.1.0 - Refund screen (Orders)
- Orders screen par refund panel ("Select the product(s) to refund") mein har refundable line par **Warehouse dropdown** + **Ship Later** checkbox (+ Ship Date).
- Chuni hui warehouse refund order line mein copy hoti hai; refund ki return delivery usi warehouse se banti hai.
- **Refund orders ki delivery hamesha Done** state mein banti hai (ship later ON ho tab bhi). Agar core validation fail ho to `stock.picking._akgr_force_done()` force-validate karta hai (fail ho to log warning).

## v20.0.1.2.0 - Lot / Serial per warehouse
- Lot/serial popup mein sirf **line ki warehouse** ke lots aate hain (us warehouse ki saari internal locations ka net stock > 0). `pos.order.line.get_existing_lots` ko optional `warehouse_id` mila (bina warehouse ke core behaviour).
- Lot/serial wale product ko **bagair lot chune order mein add nahi hone dete** (popup cancel = line hat jati hai). Sirf tab jab POS ke operation type mein lots use hon.
- Orderline par warehouse dropdown badalne par purana lot hat jata hai aur **nayi warehouse ke lots dobara chunne parte hain**. Cancel karne par purani warehouse/lot wapas.
- Faltu `pos_product_attribute.py` override hata diya (wo kuch nahi karta tha).

## v20.0.1.3.0 - "None" warehouse option
- Orderline warehouse dropdown mein **None (all lots)** option. None chunne par lot popup mein **saari warehouses ke lots** (jin ka net stock > 0) aate hain.
- Naye line par default warehouse pehle ki tarah pre-selected rehti hai.
- None wali line ki delivery order bante waqt POS ki Default Warehouse se hoti hai (`pos.order._get_line_warehouse` ka purana fallback).
