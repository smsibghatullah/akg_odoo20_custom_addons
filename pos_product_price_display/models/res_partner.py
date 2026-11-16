from odoo import models


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _get_all_identifiers(self, enrich=False):
        # Migrated partners may have an empty commercial_partner_id. Odoo then calls this
        # method on an empty recordset (ensure_one fails) when it builds the display name,
        # i.e. whenever a customer/vendor is searched on a sale order, purchase order, etc.
        if not self:
            return {}
        return super()._get_all_identifiers(enrich=enrich)

    def _get_preferred_legal_entity_identifier_vals(self):
        if not self.commercial_partner_id:
            return {}
        return super()._get_preferred_legal_entity_identifier_vals()

    def _get_preferred_tax_identifier_vals(self):
        if not self.commercial_partner_id:
            return {}
        return super()._get_preferred_tax_identifier_vals()
