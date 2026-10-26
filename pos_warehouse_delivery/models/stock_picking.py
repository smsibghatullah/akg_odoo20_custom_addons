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

    def _akgr_force_done(self):
        """Validate pickings that are still open (used for POS refunds).

        The core POS code swallows validation errors, which can leave a refund
        delivery in draft / waiting / ready.  A refund must always end 'done'.
        """
        for picking in self.filtered(lambda p: p.state not in ('done', 'cancel')):
            try:
                with self.env.cr.savepoint():
                    if picking.state == 'draft':
                        picking.action_confirm()
                    moves = picking.move_ids.filtered(lambda m: m.state not in ('done', 'cancel'))
                    for move in moves:
                        if not move.move_line_ids:
                            move._action_assign()
                        if not move.move_line_ids or move.quantity < move.product_uom_qty:
                            move.quantity = move.product_uom_qty
                    moves.picked = True
                    picking.with_context(
                        skip_backorder=True, skip_immediate=True, skip_sms=True,
                        skip_expired=True, picking_ids_not_to_backorder=picking.ids,
                    )._action_done()
            except Exception as err:  # noqa: BLE001
                _logger.warning('Refund picking %s could not be set to done: %s', picking.name, err)
            if picking.state != 'done':
                _logger.warning('Refund picking %s is still in state %s', picking.name, picking.state)
        return True

