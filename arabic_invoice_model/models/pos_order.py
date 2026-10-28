# -*- coding: utf-8 -*-
import json

from odoo import fields, models

# Notes typed on a POS order line for the kitchen/staff ("internal note") are printed too.
# Set to False to print only the order note and the customer notes of lines.
INCLUDE_LINE_INTERNAL_NOTES = True


def _clean_note(value):
    """POS notes are plain text, but restaurant style notes are stored as JSON
    like '[{"text": "No sugar", "colorIndex": 0}]'. Return readable text."""
    if not value:
        return ''
    value = str(value).strip()
    if value.startswith('[') or value.startswith('{'):
        try:
            data = json.loads(value)
            items = data if isinstance(data, list) else [data]
            texts = [str(i.get('text', '')).strip() for i in items if isinstance(i, dict)]
            if texts:
                return ', '.join(t for t in texts if t)
        except ValueError:
            pass
    return value


class PosOrder(models.Model):
    _inherit = 'pos.order'

    akg_note = fields.Text(string='POS Note', compute='_compute_akg_note')

    def _akg_collect_note(self):
        """All notes typed on the POS screen for this order, as plain text.

        Field names differ between Odoo versions, so every candidate is
        checked with `in _fields` instead of being referenced directly.
        """
        self.ensure_one()
        parts = []

        def add(text):
            text = _clean_note(text)
            if text and text not in parts:
                parts.append(text)

        for fname in ('general_note', 'note'):
            if fname in self._fields:
                add(self[fname])

        line_fields = ['customer_note']
        if INCLUDE_LINE_INTERNAL_NOTES:
            line_fields.append('note')
        for line in self.lines:
            label = ''
            for name in ('full_product_name',):
                if name in line._fields and line[name]:
                    label = line[name]
            if not label and line.product_id:
                label = line.product_id.display_name
            for fname in line_fields:
                if fname in line._fields:
                    text = _clean_note(line[fname])
                    if text:
                        entry = '%s: %s' % (label, text) if label else text
                        if entry not in parts:
                            parts.append(entry)
        return '\n'.join(parts)

    def _compute_akg_note(self):
        for order in self:
            order.akg_note = order._akg_collect_note()
