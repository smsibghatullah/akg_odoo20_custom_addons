from odoo import _, api, fields, models
from odoo.addons.base.models.res_users import check_identity
from odoo.exceptions import AccessError, UserError
from odoo.fields import Domain
from odoo.http import request

from ..models.common import GROUP_USER, SESSION_KEY, get_config
from ..models.impersonation_session import REASON_CATEGORIES


class UserImpersonationWizard(models.TransientModel):
    _name = 'user.impersonation.wizard'
    _description = 'Log In As User'

    target_id = fields.Many2one('res.users', 'Log in as', required=True)
    target_login = fields.Char(related='target_id.login', string='Login')
    target_share = fields.Boolean(related='target_id.share', string='Portal user')
    target_company_id = fields.Many2one(related='target_id.company_id', string='Main company')
    target_company_ids = fields.Many2many(related='target_id.company_ids', string='Allowed companies')
    target_groups = fields.Text('Access rights', compute='_compute_target_info')
    reason_category = fields.Selection(REASON_CATEGORIES, 'Category', required=True, default='support')
    reason = fields.Text()
    reference = fields.Char('Ticket / reference')
    read_only = fields.Boolean('Read-only session', default=lambda self: get_config(self.env)['read_only_default'],
                               help='Create, change and delete are refused while you are logged in as this user.')
    read_only_forced = fields.Boolean(compute='_compute_target_info')
    time_limit = fields.Integer('Time limit (min)', compute='_compute_target_info')
    policy_id = fields.Many2one('user.impersonation.policy', compute='_compute_target_info')
    consent_state = fields.Selection([('not_needed', 'Not needed'), ('granted', 'Access granted by the user'),
                                      ('approved', 'Approved'), ('pending', 'Waiting for the user'),
                                      ('missing', 'Consent required')], compute='_compute_target_info')
    consent_mode = fields.Char(compute='_compute_target_info')
    blocked_message = fields.Char(compute='_compute_target_info')
    min_reason_length = fields.Integer(default=lambda self: get_config(self.env)['min_reason_length'])
    landing_url = fields.Char()
    return_url = fields.Char()

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        ctx = self.env.context
        if not res.get('target_id') and ctx.get('active_model') == 'res.users':
            ids = ctx.get('active_ids') or [ctx.get('active_id')]
            if len(ids) > 1:
                raise UserError(_('Select a single user to log in as.'))
            res['target_id'] = ids[0]
        return res

    @api.depends('target_id')
    def _compute_target_info(self):
        Session = self.env['user.impersonation.session']
        portal = self.env.ref('base.group_portal')
        for wiz in self:
            target = wiz.target_id.sudo()
            groups = Session._uia_rights(target) | (target.all_group_ids & portal) if target else portal.browse()
            wiz.target_groups = '\n'.join(groups.sorted('full_name').mapped('full_name'))
            wiz.blocked_message = False
            wiz.time_limit, wiz.policy_id, wiz.read_only_forced = 0, False, False
            wiz.consent_state, wiz.consent_mode = 'not_needed', 'never'
            if not target:
                continue
            try:
                info = Session._uia_check(self.env.user, target)
            except (UserError, AccessError) as e:
                wiz.blocked_message = e.args[0]
                continue
            wiz.time_limit = info['time_limit']
            wiz.policy_id = info['policy']
            wiz.read_only_forced = info['read_only_forced']
            wiz.consent_mode, wiz.consent_state, _consent = Session._uia_consent_state(self.env.user, target)

    @api.onchange('target_id')
    def _onchange_target_id(self):
        if self.read_only_forced:
            self.read_only = True

    def action_start(self):
        self.ensure_one()
        if get_config(self.env)['require_password']:
            return self._action_start_verified()
        return self._uia_do_start()

    @check_identity
    def _action_start_verified(self):
        return self._uia_do_start()

    def _uia_do_start(self):
        self.ensure_one()
        # XML-RPC / JSON-2 API calls have no browser session of this user: no banner, return or timeout
        if not request or request.session.uid != self.env.uid or request.session.get(SESSION_KEY):
            raise UserError(_('Logging in as another user is only possible from your own web browser session.'))
        log = self.env['user.impersonation.session']._uia_start(
            self.target_id, self.reason, reason_category=self.reason_category, reference=self.reference,
            read_only=self.read_only, landing_url=self.landing_url, return_url=self.return_url)
        return {'type': 'ir.actions.act_url', 'url': log.landing_url, 'target': 'self'}

    def action_request_consent(self):
        self.ensure_one()
        reason = (self.reason or '').strip()
        if len(reason) < get_config(self.env)['min_reason_length']:
            raise UserError(_('Please give a reason of at least %s characters.', get_config(self.env)['min_reason_length']))
        self.env['user.impersonation.consent']._uia_request(
            self.target_id, reason, reason_category=self.reason_category, reference=self.reference)
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {'type': 'success', 'title': _('Request sent'),
                       'message': _('%s has been asked. Open this dialog again once they approve.', self.target_id.name),
                       'next': {'type': 'ir.actions.act_window_close'}},
        }

    # ------------------------------------------------------------------ top bar picker
    @api.model
    def _uia_picker_domain(self, query='', group_id=False):
        domain = self.env['user.impersonation.session']._uia_target_domain(self.env.user)
        if query:
            domain &= Domain('name', 'ilike', query) | Domain('login', 'ilike', query)
        if group_id:
            domain &= Domain('all_group_ids', 'in', [int(group_id)])
        return domain

    @api.model
    def uia_search_targets(self, query='', group_id=False, limit=30):
        if not self.env.user.has_group(GROUP_USER):
            raise AccessError(_('You are not allowed to log in as other users.'))
        Users = self.env['res.users'].sudo()
        me = self.env.user.sudo()
        domain = self._uia_picker_domain(query, group_id)
        policies = self.env['user.impersonation.policy'].sudo().search([])
        allowed = (lambda u: any(p._matches(me, u) for p in policies)) if policies else (lambda u: True)
        users, offset = Users.browse(), 0
        while len(users) < limit:  # policies are checked in Python: page until the list is full
            batch = Users.search(domain, offset=offset, limit=limit * 2, order='share, name')
            users |= batch.filtered(allowed)
            if len(batch) < limit * 2:
                break
            offset += limit * 2
        users = users[:limit]
        recent_ids = self.env['user.impersonation.session'].sudo().search(
            [('impersonator_id', '=', me.id)], limit=30).target_id.ids[:5]
        favorites = me.impersonation_favorite_ids
        pinned = (favorites | Users.browse(recent_ids)).filtered_domain(domain).filtered(allowed)
        result = []
        for user in pinned + (users - pinned):
            result.append({
                'id': user.id, 'name': user.name, 'login': user.login, 'portal': user.share,
                'company': user.company_id.name, 'favorite': user in favorites,
                'recent': user.id in recent_ids,
            })
        return result

    @api.model
    def uia_picker_groups(self):
        if not self.env.user.has_group(GROUP_USER):
            raise AccessError(_('You are not allowed to log in as other users.'))
        groups = self.env['res.groups'].sudo().search([('privilege_id', '!=', False)]) \
            | self.env.ref('base.group_portal') | self.env.ref('base.group_user')
        return [{'id': g.id, 'name': g.full_name} for g in groups.sorted('full_name')]

    @api.model
    def uia_toggle_favorite(self, user_id):
        if not self.env.user.has_group(GROUP_USER):
            raise AccessError(_('You are not allowed to log in as other users.'))
        me = self.env.user.sudo()
        target = self.env['res.users'].sudo().browse(int(user_id)).exists()
        if not target:
            raise UserError(_('This user does not exist.'))
        if target in me.impersonation_favorite_ids:
            me.impersonation_favorite_ids = [(3, target.id)]
            return False
        me.impersonation_favorite_ids = [(4, target.id)]
        return True
