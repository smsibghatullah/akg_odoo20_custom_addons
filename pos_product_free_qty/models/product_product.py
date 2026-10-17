# -*- coding: utf-8 -*-
import logging

from odoo import models

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def get_product_info_pos(self, *args, **kwargs):
        """Extend the data used to build the POS "Product information"
        popup so that every warehouse line also carries a `free_qty`
        value (On Hand - Reserved), i.e. the same "Free to Use Quantity"
        Odoo shows on the product form / replenishment wizard and in
        stock.replenishment.option.

        Confirmed from the server log that on this Odoo instance this
        method lives on `product.product` (not `pos.session`), and is
        called on a single-record product.product recordset - `self`
        below already *is* the product we need.

        We don't hardcode the exact key under which the core method
        returns the per-warehouse list, so instead we walk the whole
        result and patch whichever list of dicts "looks like" the
        warehouses list (i.e. its dicts have a 'name' matching a real
        warehouse and a quantity-like key). This makes the module
        resilient to small structural differences between Odoo
        point-of-sale versions.
        """
        result = super().get_product_info_pos(*args, **kwargs)

        try:
            self.ensure_one()

            warehouses = self.env['stock.warehouse'].search([])
            warehouse_by_name = {warehouse.name: warehouse for warehouse in warehouses}

            patched = self._pos_free_qty_patch_warehouses(result, self, warehouse_by_name)
            if not patched:
                _logger.warning(
                    "pos_product_free_qty: could not locate the warehouses list "
                    "in get_product_info_pos() result for product %s (%s). The "
                    "result keys were: %s. The Free Qty column will stay empty; "
                    "the XML xpath/JSON key assumptions in this module may need "
                    "updating for this Odoo version.",
                    self.id, self.display_name,
                    list(result.keys()) if isinstance(result, dict) else type(result),
                )
        except Exception:
            # Never let this optional enrichment break the POS product
            # info popup - if anything goes wrong, just log it and
            # return the original, unmodified result.
            _logger.exception("pos_product_free_qty: failed to compute free_qty for POS product info popup")

        return result

    def _pos_free_qty_patch_warehouses(self, node, product_record, warehouse_by_name):
        """Recursively look through `node` (the get_product_info_pos
        result, or a part of it) for a list of dicts that represents
        the per-warehouse inventory info, and add a 'free_qty' key to
        each of them. Returns True if such a list was found and
        patched (even partially), False otherwise.
        """
        found = False

        if isinstance(node, dict):
            for value in node.values():
                if self._pos_free_qty_patch_warehouses(value, product_record, warehouse_by_name):
                    found = True

        elif isinstance(node, list):
            # Heuristic: this is "the" warehouses list if it's a
            # non-empty list of dicts, and at least one of those dicts
            # has both a 'name' key matching a real warehouse and an
            # 'available_quantity'-like key (on-hand quantity).
            if node and all(isinstance(item, dict) for item in node):
                looks_like_warehouses = any(
                    item.get('name') in warehouse_by_name
                    and any(k for k in item if 'available' in k.lower() or 'qty' in k.lower() or 'quantity' in k.lower())
                    for item in node
                )
                if looks_like_warehouses:
                    for item in node:
                        warehouse = warehouse_by_name.get(item.get('name'))
                        if warehouse and warehouse.lot_stock_id:
                            item['free_qty'] = product_record.with_context(
                                location=warehouse.lot_stock_id.id
                            ).free_qty
                        else:
                            item['free_qty'] = 0.0
                    found = True
                else:
                    # Not the warehouses list itself - keep looking
                    # inside each item in case it's nested deeper.
                    for item in node:
                        if self._pos_free_qty_patch_warehouses(item, product_record, warehouse_by_name):
                            found = True

        return found
