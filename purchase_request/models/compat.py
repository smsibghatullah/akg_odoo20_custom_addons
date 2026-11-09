# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)
"""Small helper: Odoo 19/20 renamed several UoM fields (product_uom -> uom_id, ...).

`uom_of(record)` returns the UoM of a stock / purchase record whatever the field is
called in the running version, so the module does not break on the next rename.
"""

UOM_FIELDS = ("uom_id", "product_uom_id", "product_uom")


def uom_of(record):
    for name in UOM_FIELDS:
        field = record._fields.get(name)
        if field is not None and field.comodel_name == "uom.uom":
            return record[name]
    return record.env["uom.uom"]
