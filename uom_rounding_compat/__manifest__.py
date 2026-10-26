# -*- coding: utf-8 -*-
{
    'name': 'UoM rounding (Odoo 16 compatibility)',
    'version': '20.0.1.0.0',
    'category': 'Hidden',
    'summary': 'Gives uom.uom back the `rounding` attribute used by migrated custom modules',
    'description': """
Odoo 20 removed the `rounding` field of uom.uom (uom.round / uom.compare /
uom.is_zero use the "Product Unit" decimal precision instead).  Custom modules
migrated from older versions that still read `uom.rounding` crash with
"AttributeError: 'uom.uom' object has no attribute 'rounding'".
This module adds a read-only computed `rounding` = 10 ** -(Product Unit precision).
""",
    'depends': ['uom'],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
