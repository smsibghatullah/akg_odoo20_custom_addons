# models/res_users.py   (models/__init__.py mein:  from . import res_users)
from odoo import api, fields, models

TRANSFER_GROUPS = {
    "is_transfer_request_user": "custom_inventory_picking.group_transfer_request_user",
    "is_confirm_request_user": "custom_inventory_picking.group_confirm_request_user",
    "is_approve_transfer_user": "custom_inventory_picking.group_approve_transfer_user",
    "is_validate_transfer_user": "custom_inventory_picking.group_validate_transfer_user",
}


class ResUsers(models.Model):
    _inherit = "res.users"

    # Sirf display (compute) + editable. Save par write()/create() neeche khud group add/remove karte hain,
    # taake koi checkbox doosre ko na chhere (inverse methods ki wajah se ye masla aa raha tha).
    is_transfer_request_user = fields.Boolean(
        string="Transfer Request User", compute="_compute_transfer_groups", readonly=False)
    is_confirm_request_user = fields.Boolean(
        string="Request Received User", compute="_compute_transfer_groups", readonly=False)
    is_approve_transfer_user = fields.Boolean(
        string="Dispatched Transfer User", compute="_compute_transfer_groups", readonly=False)
    is_validate_transfer_user = fields.Boolean(
        string="Validate Transfer User", compute="_compute_transfer_groups", readonly=False)

    @api.depends("group_ids")
    def _compute_transfer_groups(self):
        groups = {f: self.env.ref(x, raise_if_not_found=False) for f, x in TRANSFER_GROUPS.items()}
        for user in self:
            for fname, group in groups.items():
                user[fname] = bool(group) and group in user.group_ids

    def _apply_transfer_flags(self, flags):
        """flags = {'is_xxx_user': True/False} -> sirf wahi groups add/remove jo form se aaye."""
        commands = []
        for fname, value in flags.items():
            group = self.env.ref(TRANSFER_GROUPS[fname], raise_if_not_found=False)
            if group:
                commands.append((4 if value else 3, group.id))
        if commands:
            super(ResUsers, self).write({"group_ids": commands})

    def write(self, vals):
        vals = dict(vals)
        flags = {f: vals.pop(f) for f in TRANSFER_GROUPS if f in vals}
        res = super().write(vals)
        if flags:
            self._apply_transfer_flags(flags)
        return res

    @api.model_create_multi
    def create(self, vals_list):
        cleaned, flags_list = [], []
        for vals in vals_list:
            vals = dict(vals)
            flags_list.append({f: vals.pop(f) for f in TRANSFER_GROUPS if f in vals})
            cleaned.append(vals)
        users = super().create(cleaned)
        for user, flags in zip(users, flags_list):
            if flags:
                user._apply_transfer_flags(flags)
        return users