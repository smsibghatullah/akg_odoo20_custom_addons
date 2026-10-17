# POS Product Info - Free Quantity

Adds a **Free Qty** column to the *Inventory* section of the POS
"Product information" popup (the one you open with the "i" icon next to
a product in the POS screen — same popup shown in your screenshot with
the **Financials / Inventory / Replenishment / Order** sections).

Free Qty = On Hand Quantity - Reserved Quantity, per warehouse — the
same value Odoo calls "Free to Use Quantity" on the product form and in
the replenishment wizard (`stock.replenishment.option.free_qty`, the
model you pasted).

## What it does

- **Backend** (`models/pos_session.py`): overrides `pos.session.get_product_info_pos`
  and adds a `free_qty` key to each warehouse entry already returned by
  Odoo, computed as `product.with_context(location=warehouse.lot_stock_id.id).free_qty`.
- **Frontend** (`static/src/xml/product_info_popup.xml`): inherits the
  `point_of_sale.ProductInfoPopup` OWL template using OWL's own
  `t-inherit` / `t-inherit-mode="extension"` syntax (not the classic
  backend `<template inherit_id="...">` view syntax — that one breaks
  the POS assets bundle, see "Fixed in this version" below) and adds
  one more `<td>` after the "forecasted" column, showing
  `warehouse.free_qty`.

No JavaScript file is needed — the popup already loops over
`productInfo.warehouses`, we just add one more `<td>` inside that loop.

### Fixed in this version (v4) - the real root cause

Turning on a debug `print()` and checking the Odoo server log finally
showed the actual RPC call being made:

```
call product.product(24019,).get_product_info_pos(2.5, 1, 647)
```

**`get_product_info_pos` lives on `product.product` on this Odoo
instance, not on `pos.session`.** All previous versions of this module
overrode `pos.session.get_product_info_pos`, which is simply never
called here - so the override code never ran at all (no error, no
warning, nothing - it just silently did nothing, which is why the
column always rendered blank).

Fixed by moving the override to `product.product` instead
(`models/product_product.py`). Since the method is now called directly
on the product record, `self` inside the override *is* the product -
no more browsing `product['id']` needed.

### Fixed in this version (v3)

Two more issues were fixed based on what actually showed up on screen:

1. **Free Qty value was blank.** The exact key/shape that
   `get_product_info_pos()` uses for the warehouses list differs
   slightly between Odoo (sub-)versions, so the earlier `result.get('warehouses')`
   lookup found nothing and silently did nothing. The Python code now
   recursively scans the whole result for whatever list "looks like"
   the warehouses list (dicts with a `name` matching a real warehouse
   and a quantity-like key) and patches that instead - so it no longer
   depends on guessing the exact key name. If it still can't find it,
   it logs a warning in the Odoo server log explaining why, instead of
   failing silently.
2. **Column position.** It was appearing between the "available" and
   "forecasted" columns instead of before "available". Based on where
   it landed on screen, `td[3]` in the warehouse row is actually the
   "available" (on-hand) column here, so the xpath now inserts the new
   column **before** `td[3]` - i.e. right after the warehouse name and
   before "On hand", as requested.

### Fixed in this version (v2)

Two separate bugs caused the POS to crash with:

```
ValueError: Template name is missing in file
'/pos_product_free_qty/static/src/xml/product_info_popup.xml'.
```

1. An earlier version used
   `<template inherit_id="point_of_sale.ProductInfoPopup" owl="1">`
   (the classic Odoo backend view-inheritance syntax). That syntax is
   for server-rendered `ir.ui.view` templates, not for templates
   embedded in the POS JS assets bundle. Fixed by switching to OWL's
   native `<t t-inherit="..." t-inherit-mode="extension">` syntax.

2. The next version wrapped that `<t t-inherit="...">` node inside its
   own `<templates>...</templates>` tag. Odoo's asset bundler
   (`assetsbundle.py`) automatically wraps any file that doesn't start
   with `<odoo>` inside a `<templates>` tag before parsing it — so
   wrapping it ourselves too resulted in a **double-wrapped**
   `<templates><templates>...`, and Odoo could no longer find our
   `<t t-inherit="...">` node as a direct child, triggering the same
   "Template name is missing" error. Fixed by removing our own
   `<templates>` wrapper — the file now contains just the raw
   `<t t-inherit="...">` node, which is exactly what Odoo expects.

This was verified by replicating Odoo's exact parsing logic from
`assetsbundle.py` against the shipped file.

## Installation

1. Copy the `pos_product_free_qty` folder into your Odoo `addons` path.
2. Restart the Odoo server.
3. Go to **Apps**, remove the "Apps" filter, search for
   **"POS Product Info - Free Quantity"**, and click Install.
4. Refresh/relaunch the POS session (the "Relaunch to update" button
   visible in your screenshot, or a hard refresh) so the new POS
   JS/XML assets are reloaded.
5. Open a product's info popup — the Inventory section should now show
   a "Free Qty" value per warehouse.

## Version compatibility note

This module targets **Odoo 16.0** (confirmed). The XML asset is loaded
through the `point_of_sale.assets` bundle, which is the correct bundle
name for 16.0 (17.0+ renamed it to `point_of_sale._assets_pos`).

After installing/upgrading, always do a **hard refresh** (Ctrl+Shift+R)
of the POS tab, or clear the assets bundle cache (Settings > Technical
mode > Regenerate Assets Bundles), since the browser/Odoo caches
compiled JS/XML assets and a normal "Relaunch to update" click does not
always recompile them.

If the popup still looks unchanged:

1. **XML xpath target.** The xpath in
   `static/src/xml/product_info_popup.xml` targets
   `div[hasclass('section-inventory-body')]//tr/td[3]`. If your Odoo
   version renders that table with different CSS classes, open the
   browser dev tools on the popup, inspect the Inventory table's HTML,
   and update the `expr` attribute to match (it just needs to point at
   the 3rd `<td>` — the "forecasted" one — inside the warehouse row).

## Uninstalling

Simply uninstall the module from Apps; it does not add any new models,
fields stored on other models, or data records, so nothing else is
affected.
