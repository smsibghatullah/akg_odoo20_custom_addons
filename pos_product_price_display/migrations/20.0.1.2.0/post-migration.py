import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Rebuild uom_uom.factor (stored computed: relative_factor * relative_uom.factor).
    Migrated units had factor = 0, which makes receipts of purchase orders fail with
    ZeroDivisionError in purchase_order_line._get_stock_move_price_unit."""
    cr.execute("SELECT id, relative_factor FROM uom_uom WHERE factor IS NULL OR factor <= 0")
    bad = cr.fetchall()
    _logger.warning("uom_uom with factor <= 0 before repair: %s", bad)

    # units whose relative_factor is unusable
    cr.execute("UPDATE uom_uom SET relative_factor = 1 WHERE relative_factor IS NULL OR relative_factor <= 0")
    # reference units (no relative unit)
    cr.execute("UPDATE uom_uom SET relative_uom_id = NULL WHERE relative_uom_id = id")
    cr.execute("UPDATE uom_uom SET factor = relative_factor WHERE relative_uom_id IS NULL")
    # children: parent factor first (chains of up to 10 levels)
    for _i in range(10):
        cr.execute("""
            UPDATE uom_uom c
               SET factor = c.relative_factor * p.factor
              FROM uom_uom p
             WHERE c.relative_uom_id = p.id
               AND p.factor > 0
               AND c.factor IS DISTINCT FROM c.relative_factor * p.factor
        """)
        if not cr.rowcount:
            break
    cr.execute("UPDATE uom_uom SET factor = 1 WHERE factor IS NULL OR factor <= 0")
    cr.execute("SELECT id, relative_factor, relative_uom_id, factor FROM uom_uom WHERE id = ANY(%s)",
               ([b[0] for b in bad] or [0],))
    _logger.warning("uom_uom repaired: %s", cr.fetchall())
