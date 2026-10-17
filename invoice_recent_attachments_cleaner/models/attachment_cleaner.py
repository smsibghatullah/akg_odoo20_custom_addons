from odoo import models, api
from datetime import datetime, timedelta

class AttachmentCleaner(models.Model):
    _inherit = 'account.move'

    @api.model
    def clean_old_invoice_attachments(self):
        three_months_ago = datetime.today() - timedelta(days=90)
        deleted_count = 0

        old_attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'account.move'),
            ('create_date', '<', three_months_ago)
        ])

        deleted_count = len(old_attachments)
        old_attachments.unlink()

        _logger = self.env['ir.logging']
        _logger.sudo().create({
            'name': 'Attachment Cleaner',
            'type': 'server',
            'dbname': self.env.cr.dbname,
            'level': 'info',
            'message': f'Deleted {deleted_count} old invoice attachments.',
            'path': 'models/attachment_cleaner.py',
            'line': 25,
            'func': 'clean_old_invoice_attachments',
        })

        return True
