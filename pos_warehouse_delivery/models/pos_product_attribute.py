from odoo import api, models
from odoo.fields import Domain


class ProductAttribute(models.Model):
    _inherit = 'product.attribute'

    @api.model
    def _load_pos_data_domain(self, *args, **kwargs):
        domain = super()._load_pos_data_domain(*args, **kwargs)
        # Jin attributes ki lines POS products par hain, unhe bhi load karo
        lines = self.env['product.template.attribute.line'].sudo().search([
            ('product_tmpl_id.available_in_pos', '=', True),
            ('product_tmpl_id.active', '=', True),
        ])
        return Domain.OR([Domain(domain), Domain('id', 'in', lines.attribute_id.ids)])