# -*- coding: utf-8 -*-
from odoo import api, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    @api.model
    def _load_pos_data_read(self, records, config):
        """Add `_price_manager` to every employee sent to the POS.

        Standard `_role` becomes 'manager' as soon as the employee's user is in the POS Manager group,
        even when the employee is a Cashier in the POS settings. For the price button the POS settings win.
        """
        read_records = super()._load_pos_data_read(records, config)
        managers = set(config.manager_employee_ids.ids)
        others = (set(config.cashier_employee_ids.ids)
                  | set(config.supervised_employee_ids.ids)
                  | set(config.restrictive_employee_ids.ids))
        for employee in read_records:
            emp_id = employee['id']
            if emp_id in managers:
                employee['_price_manager'] = True
            elif emp_id in others:
                employee['_price_manager'] = False
            else:
                employee['_price_manager'] = employee.get('_role') == 'manager'
        return read_records
