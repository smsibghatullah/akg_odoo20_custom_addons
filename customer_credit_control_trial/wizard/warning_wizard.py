# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class WarningWizard(models.TransientModel):
    _name = "warning.wizard"
    _description = "Warning Wizard"

    name = fields.Char("Name")
    message = fields.Text("Message")
