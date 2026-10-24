# -*- coding: utf-8 -*-
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)

# Safety limit so a badly out-of-sync sequence can never loop forever.
MAX_NAME_TRIES = 10000


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.model
    def _get_unique_picking_name(self, sequence, company_id):
        """Next sequence value that is not already used by another picking
        of the same company.

        Fixes "Reference must be unique per company!" when the sequence of
        an operation type is behind already existing (e.g. migrated)
        pickings, or when two operation types share the same prefix.
        Each skipped number also advances the sequence, so it heals itself.
        """
        Picking = self.sudo()
        sequence = sequence.sudo()
        name = sequence.next_by_id()
        tries = 0
        while (name and tries < MAX_NAME_TRIES and Picking.search_count(
                [('name', '=', name), ('company_id', '=', company_id)],
                limit=1)):
            tries += 1
            name = sequence.next_by_id()
        if tries:
            _logger.warning(
                'Picking sequence %s (%s) was out of sync: skipped %s used '
                'number(s), using %s', sequence.id, sequence.prefix, tries, name)
        return name or '/'

    @api.model_create_multi
    def create(self, vals_list):
        PickingType = self.env['stock.picking.type']
        for vals in vals_list:
            if vals.get('name') not in (None, False, '/'):
                continue
            if not vals.get('picking_type_id'):
                continue
            picking_type = PickingType.browse(vals['picking_type_id'])
            if not picking_type.sequence_id:
                continue
            company_id = (vals.get('company_id')
                          or picking_type.company_id.id
                          or self.env.company.id)
            vals['name'] = self._get_unique_picking_name(
                picking_type.sequence_id, company_id)
        return super().create(vals_list)