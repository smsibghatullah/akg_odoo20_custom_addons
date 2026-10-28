# -*- coding: utf-8 -*-
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)

# (view name, parent view xml id, model, arch). The views are created from code
# (called from data/views_note.xml) so a layout difference in a core form can
# never stop the module from installing: a failure is only logged.
NOTE_VIEWS = [
    ('akg.pos.order.form.note', 'point_of_sale.view_pos_pos_form', 'pos.order',
     '<data><xpath expr="//notebook" position="before">'
     '<group invisible="not akg_note"><field name="akg_note" string="POS Note" readonly="1"/></group>'
     '</xpath></data>'),
    ('akg.account.move.form.pos.note', 'account.view_move_form', 'account.move',
     '<data><xpath expr="//notebook" position="before">'
     '<group invisible="not pos_note"><field name="pos_note" string="POS Note" readonly="1"/></group>'
     '</xpath></data>'),
]


class IrUiView(models.Model):
    _inherit = 'ir.ui.view'

    @api.model
    def _akg_ensure_note_views(self):
        for name, parent_xmlid, model, arch in NOTE_VIEWS:
            parent = self.env.ref(parent_xmlid, raise_if_not_found=False)
            if not parent:
                _logger.warning('arabic_invoice_model: view %s not found, POS note not shown there', parent_xmlid)
                continue
            try:
                with self.env.cr.savepoint():
                    view = self.search([('name', '=', name), ('inherit_id', '=', parent.id)], limit=1)
                    if view:
                        view.write({'arch_base': arch})
                    else:
                        self.create({
                            'name': name,
                            'model': model,
                            'inherit_id': parent.id,
                            'mode': 'extension',
                            'type': 'form',
                            'arch_base': arch,
                        })
            except Exception:
                _logger.warning('arabic_invoice_model: could not add the POS note to %s', parent_xmlid, exc_info=True)
        return True
