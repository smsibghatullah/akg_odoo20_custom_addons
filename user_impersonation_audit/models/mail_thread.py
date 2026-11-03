from odoo import _, fields, models
from odoo.exceptions import UserError

from .common import current_impersonation, get_config


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def _message_compute_author(self, author_id=None, email_from=None):
        """Messages posted while impersonating are signed by the real user, not the target."""
        imp = current_impersonation()
        if imp and author_id is None and not email_from and self.env.uid == imp['target_uid']:
            author_id = self.env['res.users'].sudo().browse(imp['real_uid']).partner_id.id
        return super()._message_compute_author(author_id, email_from)

    def message_post(self, **kwargs):
        imp = current_impersonation()
        if not imp or self.env.uid != imp['target_uid']:
            return super().message_post(**kwargs)
        author_id = kwargs.get('author_id')
        if self.env.su and author_id and author_id != self.env.user.partner_id.id:
            # system message posted by the framework under another author (e.g. the OdooBot welcome);
            # the author cannot be chosen from the web client, so this is never the impersonator
            return super().message_post(**kwargs)
        if imp.get('read_only'):
            raise UserError(_('Read-only session: you cannot post messages while you are logged in as another user.'))
        message = super().message_post(**kwargs)
        if len(self) == 1 and get_config(self.env)['track_changes']:
            self.env['user.impersonation.activity'].sudo().create({
                'session_id': imp['log_id'], 'date': fields.Datetime.now(), 'operation': 'message',
                'model': self._name, 'model_description': self.env['ir.model']._get(self._name).name,
                'res_id': self.id, 'record_name': (self.sudo().display_name or '')[:250],
                'summary': _('Message posted as the real user'),
            })
        return message
