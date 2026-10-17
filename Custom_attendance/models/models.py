from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import ValidationError
from odoo.tools import format_datetime

class Attendance(models.Model):
    _inherit = 'hr.attendance'

    def custom_check_in(self):
        employee = self.env['hr.employee'].search([('id', '=', self.id)], limit=1)
        if employee:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            current_date = datetime.now().strftime('%Y-%m-%d')

            # current_time = datetime.now().strftime('%m/%d/%Y %H:%M:%S') #02/11/2023 15:12:12
            last_attendance = self.env['hr.attendance'].search([('employee_id', '=', employee.id),('check_in', '<=', current_time)], order='id desc',
                                                               limit=1)
            if last_attendance:
                # last_date = last_attendance.check_in.strftime('%Y-%m-%d')
                # if current_date != last_date:
                    self.env['hr.attendance'].create({
                        'employee_id': employee.id,
                        'check_in': current_time,
                    })
                    return
            else:
                self.env['hr.attendance'].create({
                    'employee_id': employee.id,
                    'check_in': current_time,
                })
                return

    def custom_check_out(self):
        employee = self.env['hr.employee'].search([('id', '=', self.id)], limit=1)
        if employee:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            current_date = datetime.now().strftime('%Y-%m-%d')

            # current_time = datetime.now().strftime('%m/%d/%Y %H:%M:%S') #02/11/2023 15:12:12
            last_attendance = self.env['hr.attendance'].search([('employee_id', '=', employee.id),('check_in', '<=', current_time)], order='id desc',
                                                               limit=1)
            if last_attendance and last_attendance.check_out == False:
                last_attendance.write({'check_out': current_time})
                return
            else:
                if last_attendance and last_attendance.check_out and str(last_attendance.check_out) < current_time:
                    raise ValidationError(
                        _("Cannot create new attendance record for %(empl_name)s, the employee was already checked in on %(datetime)s") % {
                            'empl_name': employee.name,
                            'datetime': format_datetime(self.env, current_time, dt_format=False),
                        })

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    @api.constrains('payment_method_line_id')
    def _check_payment_method_line_id(self):
        ''' Ensure the 'payment_method_line_id' field is not null.
        Can't be done using the regular 'required=True' because the field is a computed editable stored one.
        '''
        for pay in self:

            if not pay.payment_method_line_id:
                raise ValidationError(_("Please define a payment method line on your payment."))
            elif pay.payment_method_line_id.journal_id and pay.payment_method_line_id.journal_id != pay.journal_id:
                payment_method_line = self.env['account.payment.method.line'].search([
                ('journal_id', '=', pay.journal_id.id),
                ('payment_method_id', '=', pay.payment_method_line_id.payment_method_id.id)
                ], limit=1)
                if payment_method_line:
                    pay.payment_method_line_id = payment_method_line
            # else:
            #         raise ValidationError(_("The selected payment method is not available for this payment, please select the payment method again."))
