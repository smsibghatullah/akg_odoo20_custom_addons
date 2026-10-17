from odoo import models, fields, api,_


class StockPicking(models.Model):
    _inherit = "stock.picking"


    partner_id = fields.Many2one(
        comodel_name="res.partner",
        domain="[('user_ids', '!=', False)]",  
    )


    # Odoo 20: extend the core selection instead of re-declaring the whole field,
    # so the core compute / tracking / help text stay in sync with the framework.
    state = fields.Selection(
        selection_add=[
            ('initial_request', 'Initial Request'),
            ('confirm_transfer', 'Request Received'),
            ('approved_manager', 'Dispatched'),
            ('validate_transfer', 'Validate Transfer'),
        ],
        ondelete={
            'initial_request': lambda recs: recs.write({'state': 'draft'}),
            'confirm_transfer': lambda recs: recs.write({'state': 'draft'}),
            'approved_manager': lambda recs: recs.write({'state': 'draft'}),
            'validate_transfer': lambda recs: recs.write({'state': 'draft'}),
        },
    )

    # Helper fields used by the form view: Odoo 17+ no longer supports returning a
    # 'domain' from an @api.onchange, so the dynamic domains are computed here and
    # referenced from the view.
    allowed_picking_type_ids = fields.Many2many(
        'stock.picking.type', compute='_compute_allowed_domains')
    allowed_src_location_ids = fields.Many2many(
        'stock.location', compute='_compute_allowed_domains', relation='x_picking_allowed_src_loc_rel')
    allowed_dest_location_ids = fields.Many2many(
        'stock.location', compute='_compute_allowed_domains', relation='x_picking_allowed_dest_loc_rel')
    restrict_dest_location = fields.Boolean(compute='_compute_allowed_domains')

    @api.depends('partner_id')
    def _compute_allowed_domains(self):
        StockLocation = self.env['stock.location']
        PickingType = self.env['stock.picking.type']
        login_wh = self.env.user.property_warehouse_id
        for picking in self:
            types = PickingType.search([('code', '=', 'internal')])
            src_locations = StockLocation.search([('usage', '=', 'internal')])
            partner_user = picking.partner_id.user_ids[:1]
            if partner_user and partner_user.property_warehouse_id:
                wh_types = PickingType.search([
                    ('warehouse_id', '=', partner_user.property_warehouse_id.id),
                    ('code', '=', 'internal'),
                ])
                types = wh_types or types
                default_src = wh_types[:1].default_location_src_id
                if default_src:
                    src_locations = default_src
            picking.allowed_picking_type_ids = types
            picking.allowed_src_location_ids = src_locations
            if login_wh and login_wh.lot_stock_id:
                picking.restrict_dest_location = True
                picking.allowed_dest_location_ids = login_wh.lot_stock_id
            else:
                picking.restrict_dest_location = False
                picking.allowed_dest_location_ids = StockLocation

    @api.depends('state', 'picking_type_code')
    def _compute_validate_button_style(self):
        """Internal transfers are validated through the custom approval workflow:
        hide the standard Validate buttons for them."""
        super()._compute_validate_button_style()
        for picking in self.filtered(lambda p: p.picking_type_code == 'internal'):
            picking.validate_button_style = 'invisible'

    def action_confirm(self):
        """
        Standard Odoo logic generates stock moves.
        After that, we force state = 'initial_request'
        """
        res = super(StockPicking, self).action_confirm()
        # for picking in self:
        #     picking.state = 'initial_request'
        #     res = super(StockPicking, self).action_confirm()
        for picking in self:
            if picking.picking_type_id.code == "internal":
                picking.state = "initial_request"
        return res
        # return res

    def action_initial_approve(self):
        """ Move from Initial Request -> Confirm Transfer """
        for picking in self:
            picking.state = 'confirm_transfer'
            picking._notify_group_users(
                "custom_inventory_picking.group_confirm_request_user",  # XMLID of group
                _("Transfer Request Approved"),
                _("A transfer request has been approved and is awaiting your confirmation.")
            )


    def action_confirm_transfer_approve(self):
        """ Move from Confirm Transfer -> Approved Manager """
        for picking in self:
            picking.state = 'approved_manager'
            picking._notify_group_users(
                "custom_inventory_picking.group_approve_transfer_user",
                _("Transfer Request Needs Approval"),
                _("A transfer is waiting for your manager approval.")
            )

    def action_approved_manager_approve(self):
        """ Move from Approved Manager -> Validate Transfer """
        for picking in self:
            picking.state = 'validate_transfer'
            picking._notify_group_users(
                "custom_inventory_picking.group_validate_transfer_user",
                _("Transfer Approved"),
                _("A transfer has been approved and is ready for validation.")
            )

    def action_validate_transfer_approve(self):
        """
        Final step: call Odoo's normal validation
        This ensures stock quantities are updated, moves are done, etc.
        """
        return super(StockPicking, self).button_validate()

    def _notify_group_users(self, group_xmlid, subject, body):
        """Utility: send mail to all users of a group"""
        group = self.env.ref(group_xmlid)
        if not group:
            return
        users = group.user_ids
        partners = users.mapped("partner_id")

        if partners:
            mail_values = {
                'subject': subject,
                'body_html': body,
                'email_from': self.env.user.email or 'noreply@example.com',
                'recipient_ids': [(6, 0, partners.ids)],
            }
            self.env['mail.mail'].create(mail_values).send()



    @api.onchange("partner_id")
    def _onchange_partner_id_set_domains(self):
        """Set picking type / destination location from the partner's user warehouse.
        (The matching domains are provided by `_compute_allowed_domains`.)"""
        if self.partner_id and self.partner_id.user_ids:
            partner_user = self.partner_id.user_ids[0]
            if partner_user.property_warehouse_id:
                internal_type = self.env["stock.picking.type"].search([
                    ("warehouse_id", "=", partner_user.property_warehouse_id.id),
                    ("code", "=", "internal"),
                ], limit=1)
                if internal_type:
                    self.picking_type_id = internal_type

        login_user = self.env.user
        if login_user.property_warehouse_id and login_user.property_warehouse_id.lot_stock_id:
            self.location_dest_id = login_user.property_warehouse_id.lot_stock_id

    @api.onchange("picking_type_id")
    def _onchange_picking_type_id_custom(self):
        """Re-apply custom location/domain after Odoo's default onchange."""
        login_user = self.env.user
        if login_user.property_warehouse_id and login_user.property_warehouse_id.lot_stock_id:
            stock_location = login_user.property_warehouse_id.lot_stock_id
            self.location_dest_id = stock_location
        if self.picking_type_id and self.picking_type_id.default_location_src_id:
            self.location_id = self.picking_type_id.default_location_src_id

    # @api.model
    # def default_get(self, fields_list):
    #     """Set dest_location_id based on the logged in user's warehouse."""
    #     res = super().default_get(fields_list)
    #     user = self.env.user
    #     if user.property_warehouse_id and user.property_warehouse_id.lot_stock_id:
    #         res["dest_location_id"] = user.property_warehouse_id.lot_stock_id.id
    #     return res

class StockMove(models.Model):
    _inherit = "stock.move"

    state = fields.Selection(selection_add=[
        ("initial_request", "Initial Request"),
        ("confirm_transfer", "Confirm Transfer"),
        ("approved_manager", "Approved By Manager"),
    ], ondelete={
        "initial_request": "set default",
        "confirm_transfer": "set default",
        "approved_manager": "set default",
    })




class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    picking_state = fields.Selection(
        related="picking_id.state",   
        store=True,
        readonly=True,
    )
    picking_type_code = fields.Selection(
        related="picking_id.picking_type_code",
        store=True,
        readonly=True,
    )
