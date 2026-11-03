import secrets
from datetime import timedelta

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

from .common import current_impersonation
from .impersonation_session import REASON_CATEGORIES

CONSENT_VALIDITY_MINUTES = 60


class UserImpersonationConsent(models.Model):
    _name = 'user.impersonation.consent'
    _description = 'Impersonation Consent Request'
    _inherit = ['mail.thread']
    _order = 'id desc'

    requester_id = fields.Many2one('res.users', 'Requested by', required=True, ondelete='cascade', index=True)
    target_id = fields.Many2one('res.users', 'User asked', required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one('res.company', required=True, index=True)
    reason_category = fields.Selection(REASON_CATEGORIES, 'Category', default='support')
    reason = fields.Text()
    reference = fields.Char('Ticket / reference')
    state = fields.Selection([('pending', 'Waiting for answer'), ('approved', 'Approved'), ('refused', 'Refused'),
                              ('used', 'Used'), ('expired', 'Expired')],
                             default='pending', required=True, index=True, tracking=True)
    decision_date = fields.Datetime('Decided on', readonly=True)
    valid_until = fields.Datetime('Valid until', readonly=True, help='An approval must be used before this time.')
    access_token = fields.Char(groups='base.group_system', copy=False)
    session_id = fields.Many2one('user.impersonation.session', readonly=True)

    @api.depends('requester_id', 'target_id')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = _('%(who)s asks to log in as %(whom)s',
                                 who=rec.requester_id.name or '', whom=rec.target_id.name or '')

    @api.model
    def _uia_request(self, target, reason, reason_category='support', reference=False):
        """Create a pending request and notify the target (inbox or email, per their preference)."""
        requester = self.env.user
        Session = self.env['user.impersonation.session']
        Session._uia_check(requester, target)
        mode, state, existing = Session._uia_consent_state(requester, target)
        if state in ('not_needed', 'granted', 'approved'):
            raise UserError(_('No consent is needed: you can log in as %s now.', target.name))
        if state == 'pending':
            return existing
        consent = self.sudo().create({
            'requester_id': requester.id, 'target_id': target.id, 'company_id': self.env.company.id,
            'reason': reason, 'reason_category': reason_category, 'reference': reference,
            'access_token': secrets.token_urlsafe(24),
        })
        consent._uia_notify_target()
        return consent

    def _uia_url(self, decision):
        self.ensure_one()
        base = self.get_base_url()
        return '%s/impersonation/consent/%s/%s?token=%s' % (base, self.id, decision, self.sudo().access_token)

    def _uia_notify_target(self):
        self.ensure_one()
        category = dict(self._fields['reason_category']._description_selection(self.env)).get(self.reason_category, '')
        body = Markup(
            '<p>%(intro)s</p><p><b>%(reason_label)s</b> %(category)s: %(reason)s%(ref)s</p>'
            '<p><a href="%(approve)s" style="background-color:#1f7a4d;color:#fff;padding:8px 14px;'
            'border-radius:6px;text-decoration:none;">%(approve_label)s</a> &#160; '
            '<a href="%(refuse)s" style="background-color:#a12a2a;color:#fff;padding:8px 14px;'
            'border-radius:6px;text-decoration:none;">%(refuse_label)s</a></p><p>%(outro)s</p>'
        ) % {
            'intro': _('%s asks to log in to your account to help you.', self.requester_id.name),
            'reason_label': _('Reason:'),
            'category': category,
            'reason': self.reason or '',
            'ref': (' (%s)' % self.reference) if self.reference else '',
            'approve': self._uia_url('approve'),
            'refuse': self._uia_url('refuse'),
            'approve_label': _('Allow access'),
            'refuse_label': _('Refuse'),
            'outro': _('If you allow it, the approval is valid for %s minutes. Everything done in your '
                       'account is recorded and you will see a note on your profile.', CONSENT_VALIDITY_MINUTES),
        }
        self.sudo().message_post(
            body=body, partner_ids=self.target_id.partner_id.ids, message_type='comment',
            subtype_xmlid='mail.mt_comment', subject=_('Access request to your account'))

    def _uia_decide(self, decision, user):
        """Approve or refuse; only the target user can decide, only once."""
        self.ensure_one()
        if current_impersonation():
            raise UserError(_('Return to your own account before answering an access request.'))
        if user != self.target_id:
            raise AccessError(_('Only %s can answer this request.', self.target_id.name))
        if self.state != 'pending':
            raise UserError(_('This request was already answered or has expired.'))
        now = fields.Datetime.now()
        vals = {'state': 'approved' if decision == 'approve' else 'refused', 'decision_date': now}
        if decision == 'approve':
            vals['valid_until'] = now + timedelta(minutes=CONSENT_VALIDITY_MINUTES)
        self.sudo().write(vals)
        msg = _('%s allowed access to their account.', user.name) if decision == 'approve' \
            else _('%s refused access to their account.', user.name)
        self.sudo().message_post(body=msg, partner_ids=self.requester_id.partner_id.ids,
                                 message_type='comment', subtype_xmlid='mail.mt_comment')
        return True

    def action_approve(self):
        return self._uia_decide('approve', self.env.user)

    def action_refuse(self):
        return self._uia_decide('refuse', self.env.user)
