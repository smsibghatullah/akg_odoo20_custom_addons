import hashlib
import ipaddress
import logging
import re
import time
from datetime import datetime, timedelta

import pytz
from markupsafe import Markup, escape

from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.fields import Domain
from odoo.http import request
from odoo.http.session import finalize, logout, session_store
from odoo.tools.misc import consteq

from .common import (
    GROUP_MANAGER, GROUP_USER, SESSION_KEY, current_impersonation, get_config, separate_env,
)

_logger = logging.getLogger(__name__)

REASON_CATEGORIES = [
    ('support', 'Support ticket'),
    ('access_test', 'Access test'),
    ('training', 'Training'),
    ('other', 'Other'),
]
END_REASONS = [
    ('manual', 'Returned manually'),
    ('timeout', 'Time limit reached'),
    ('idle', 'Idle timeout'),
    ('forced', 'Ended by a manager'),
    ('logout', 'Logged out'),
    ('expired', 'Expired (browser closed)'),
]


def _fingerprint(user):
    """Uncached hash of the real user's credentials (password, login, active). Compared on return:
    if the account changed meanwhile, the browser is logged out instead of switched back."""
    user = user.sudo()
    return user._session_token_hash_compute('uia-fp-%d' % user.id, user._session_token_get_values()) or ''


def safe_local_url(url, default):
    url = (url or '').strip()
    if not url.startswith('/') or url.startswith('//') or '\\' in url or re.search(r'[\x00-\x20\x7f]', url):
        return default
    return url


def switch_session_user(env, user):
    """Make the current browser session belong to `user`, exactly like a login does
    (session.finalize: user context, session token, sid rotation)."""
    session = request.session
    session['pre_login'] = user.login
    session['pre_uid'] = user.id
    finalize(session, env)


def restore_real_user(env, imp):
    """Give the browser session back to the real user. Returns False if the real account changed
    or was archived meanwhile: the session is then logged out instead."""
    session = request.session
    session.pop(SESSION_KEY, None)
    real = env['res.users'].sudo().browse(imp['real_uid']).exists()
    if not real or not real.active or not consteq(_fingerprint(real), imp.get('real_fp') or ''):
        logout(session, keep_db=True)
        return False
    switch_session_user(env, real)
    if imp.get('identity_check'):
        session['identity-check-last'] = imp['identity_check']
    if imp.get('cids'):
        request.future_response.set_cookie('cids', imp['cids'])
    else:
        request.future_response.set_cookie('cids', max_age=0)
    return True


class UserImpersonationSession(models.Model):
    _name = 'user.impersonation.session'
    _description = 'Impersonation Session'
    _order = 'start_date desc, id desc'

    name = fields.Char(compute='_compute_name', store=True)
    state = fields.Selection([('active', 'Active'), ('ended', 'Ended')], default='active',
                             required=True, index=True)
    impersonator_id = fields.Many2one('res.users', 'Impersonator', required=True, ondelete='restrict', index=True)
    target_id = fields.Many2one('res.users', 'Logged in as', required=True, ondelete='restrict', index=True)
    target_share = fields.Boolean('Portal user')
    company_id = fields.Many2one('res.company', required=True, index=True)
    policy_id = fields.Many2one('user.impersonation.policy', ondelete='set null')
    consent_id = fields.Many2one('user.impersonation.consent', ondelete='set null')
    reason_category = fields.Selection(REASON_CATEGORIES, 'Category', required=True, default='support')
    reason = fields.Text(required=True)
    reference = fields.Char('Ticket / reference')
    read_only = fields.Boolean('Read-only')
    start_date = fields.Datetime('Started', required=True, default=fields.Datetime.now, index=True)
    planned_end_date = fields.Datetime('Time limit')
    end_date = fields.Datetime('Ended')
    duration = fields.Float('Duration (min)', compute='_compute_duration', store=True, aggregator='sum')
    end_reason = fields.Selection(END_REASONS, 'End reason')
    ended_by_id = fields.Many2one('res.users', 'Ended by', ondelete='set null')
    extended = fields.Boolean()
    extension_reason = fields.Text()
    ip_address = fields.Char('IP address')
    user_agent = fields.Char('Browser')
    session_hash = fields.Char('Session fingerprint',
                               help='SHA-256 hash of the browser session id. The session id itself is never stored.')
    landing_url = fields.Char('Landing page')
    session_identifier = fields.Char(groups='base.group_system', copy=False,
                                     help='Public half of the impersonated browser session id (as in Devices), '
                                          'used to log that browser out if the app is uninstalled mid-session.')
    activity_ids = fields.One2many('user.impersonation.activity', 'session_id', 'Activity')
    activity_count = fields.Integer(compute='_compute_counts')
    change_count = fields.Integer('Records changed', compute='_compute_counts')

    _start_idx = models.Index('(impersonator_id, start_date DESC)')

    @api.depends('impersonator_id', 'target_id')
    def _compute_name(self):
        for rec in self:
            rec.name = _('%(who)s as %(whom)s', who=rec.impersonator_id.name or '', whom=rec.target_id.name or '')

    @api.depends('start_date', 'end_date')
    def _compute_duration(self):
        for rec in self:
            if rec.start_date and rec.end_date:
                rec.duration = round((rec.end_date - rec.start_date).total_seconds() / 60.0, 1)
            else:
                rec.duration = 0.0

    def _compute_counts(self):
        for rec in self:
            acts = rec.activity_ids
            rec.activity_count = len(acts)
            rec.change_count = len(acts.filtered(lambda a: a.operation in ('create', 'write', 'unlink')))

    # ------------------------------------------------------------------ append-only
    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.su:
            raise AccessError(_('Impersonation records are written by the application only; they cannot be created, changed or deleted by hand.'))
        return super().create(vals_list)

    def write(self, vals):
        if not self.env.su:
            raise AccessError(_('Impersonation records are written by the application only; they cannot be created, changed or deleted by hand.'))
        return super().write(vals)

    def unlink(self):
        if not self.env.su:
            raise AccessError(_('Impersonation records are written by the application only; they cannot be created, changed or deleted by hand.'))
        return super().unlink()

    # ------------------------------------------------------------------ rules
    @api.model
    def _uia_config(self):
        return get_config(self.env)

    @api.model
    def _uia_check(self, impersonator, target, ip=None, now=None):
        """Raise UserError/AccessError when `impersonator` may not log in as `target`.
        Return dict(policy, time_limit, read_only_forced)."""
        conf = get_config(self.env)
        impersonator, target = impersonator.sudo(), target.sudo()
        if not impersonator.has_group(GROUP_USER):
            raise AccessError(_('You are not allowed to log in as other users.'))
        if request and request.session.get(SESSION_KEY):
            raise UserError(_('You are already logged in as another user. Return to your account first.'))
        if not target.exists():
            raise UserError(_('This user does not exist.'))
        if target.id == SUPERUSER_ID:
            raise UserError(_('The superuser (OdooBot) can never be impersonated.'))
        if target == impersonator:
            raise UserError(_('You cannot log in as yourself.'))
        if not target.active:
            raise UserError(_('%s is archived and cannot be impersonated.', target.name))
        if target._is_public():
            raise UserError(_('The public user cannot be impersonated.'))
        if target.impersonation_protected or target.all_group_ids.filtered('impersonation_protected'):
            raise UserError(_('%s is protected and can never be impersonated.', target.name))
        if target._is_admin() and not (conf['allow_admin_targets'] and impersonator._is_system()):
            raise UserError(_('%s is an administrator. Administrators cannot be impersonated.', target.name))
        extra = self._uia_rights(target) - self._uia_rights(impersonator)
        if extra:
            raise UserError(_(
                '%(user)s has rights you do not have (%(groups)s). You can only log in as users with the same or fewer rights.',
                user=target.name, groups=', '.join(extra[:5].mapped('full_name'))))
        foreign = target.company_ids - impersonator.company_ids
        if foreign:
            raise UserError(_('%(user)s also works in companies you have no access to (%(companies)s).',
                              user=target.name, companies=', '.join(foreign.mapped('name'))))
        self._uia_check_network(conf, ip)
        self._uia_check_hours(conf, impersonator, now)
        policy = self.env['user.impersonation.policy'].sudo()
        policies = policy.search([])
        if policies:
            policy = next((p for p in policies if p._matches(impersonator, target)), policy)
            if not policy:
                raise AccessError(_('No impersonation policy lets you log in as %s.', target.name))
        limit = (policy.time_limit if policy and policy.time_limit else conf['time_limit']) or 60
        limit = min(limit, conf['max_time_limit'] or limit)
        return {'policy': policy, 'time_limit': limit, 'read_only_forced': bool(policy and policy.force_read_only)}

    @api.model
    def _uia_rights(self, user):
        return self._uia_rights_of(user.sudo().all_group_ids)

    @api.model
    def _uia_rights_of(self, groups):
        """Access rights that matter for the privilege ceiling: the user roles, groups with a privilege
        (Sales / Administrator, Export / Allowed...) and any group that grants model access or record
        rules. Portal, public and every group they imply (e.g. website's public access groups) are what
        every portal user gets, lower than an internal impersonator, and are left out; pure feature
        flags without access rights are ignored."""
        roles = self.env.ref('base.group_user') | self.env.ref('base.group_erp_manager') | self.env.ref('base.group_system')
        lower = self.env.ref('base.group_portal') | self.env.ref('base.group_public')
        groups = groups.sudo() - lower - lower.all_implied_ids
        return groups.filtered(lambda g: g.privilege_id or g.access_ids) | (groups & roles)

    @api.model
    def _uia_target_domain(self, impersonator):
        """Users that _uia_check does not refuse for who they are (policies, consent, network and hours
        aside): same rules, as one search domain for the picker."""
        conf = get_config(self.env)
        impersonator = impersonator.sudo()
        Groups = self.env['res.groups'].sudo().with_context(active_test=False)
        too_high = self._uia_rights_of(Groups.search([])) - self._uia_rights(impersonator)
        too_high |= Groups.search([('impersonation_protected', '=', True)])
        too_high |= self.env.ref('base.group_public')
        if not (conf['allow_admin_targets'] and impersonator._is_system()):
            too_high |= self.env.ref('base.group_erp_manager')
        other_companies = self.env['res.company'].sudo().search([('id', 'not in', impersonator.company_ids.ids)])
        return Domain([
            ('id', 'not in', [impersonator.id, SUPERUSER_ID]), ('active', '=', True),
            ('impersonation_protected', '=', False),
            # not 'all_group_ids not in': on that computed path it means "some group outside"
            ('group_ids', 'not any', [('all_implied_ids', 'in', too_high.ids)]),
            ('company_ids', 'not in', other_companies.ids),
        ])

    @api.model
    def _uia_parse_networks(self, text):
        nets = []
        for entry in re.split(r'[\s,;]+', text or ''):
            if entry:
                nets.append(ipaddress.ip_network(entry, strict=False))
        return nets

    @api.model
    def _uia_check_network(self, conf, ip=None):
        if not conf['ip_allowlist']:
            return
        if ip is None and request:
            ip = request.httprequest.remote_addr
        try:
            nets = self._uia_parse_networks(conf['ip_allowlist'])
            addr = ipaddress.ip_address(ip or '')
        except ValueError:
            nets, addr = [], None
        if not addr or not any(addr in net for net in nets):
            raise AccessError(_('Logging in as another user is not allowed from your network address (%s).', ip or '?'))

    @api.model
    def _uia_check_hours(self, conf, impersonator, now=None):
        start, end = conf['hours_from'], conf['hours_to']
        if start == end:
            return
        now = now or datetime.now(pytz.utc)
        if now.tzinfo is None:
            now = pytz.utc.localize(now)
        local = now.astimezone(pytz.timezone(impersonator.tz or 'UTC'))
        hour = local.hour + local.minute / 60.0
        inside = start <= hour < end if start < end else (hour >= start or hour < end)
        if not inside:
            raise AccessError(_('Logging in as another user is only allowed between %(start)s and %(end)s.',
                                start=self._uia_hhmm(start), end=self._uia_hhmm(end)))

    @staticmethod
    def _uia_hhmm(value):
        return '%02d:%02d' % (int(value), round((value % 1) * 60))

    @api.model
    def _uia_consent_state(self, impersonator, target):
        """Return (mode, state, consent). state: not_needed, granted, approved, pending or missing."""
        conf = get_config(self.env)
        target = target.sudo()
        mode = target.impersonation_consent if target.impersonation_consent not in (False, 'default') \
            else conf['default_consent']
        consent = self.env['user.impersonation.consent'].sudo()
        if mode != 'require':
            return mode, 'not_needed', consent
        now = fields.Datetime.now()
        if target.impersonation_grant_until and target.impersonation_grant_until > now:
            return mode, 'granted', consent
        base = [('requester_id', '=', impersonator.id), ('target_id', '=', target.id)]
        approved = consent.search(base + [('state', '=', 'approved'), ('valid_until', '>', now)], limit=1)
        if approved:
            return mode, 'approved', approved
        pending = consent.search(base + [('state', '=', 'pending')], limit=1)
        return mode, ('pending' if pending else 'missing'), pending

    # ------------------------------------------------------------------ start / end
    @api.model
    def _uia_start(self, target, reason, reason_category='support', reference=False, read_only=None,
                   landing_url=False, return_url=False):
        impersonator = self.env.user
        conf = get_config(self.env)
        info = self._uia_check(impersonator, target)
        reason = (reason or '').strip()
        if len(reason) < conf['min_reason_length']:
            raise UserError(_('Please give a reason of at least %s characters.', conf['min_reason_length']))
        mode, cstate, consent = self._uia_consent_state(impersonator, target)
        if cstate in ('pending', 'missing'):
            raise UserError(_('%s must approve before you can log in as them. Ask for consent first.', target.name))
        if read_only is None:
            read_only = conf['read_only_default']
        read_only = bool(read_only) or info['read_only_forced']
        now = fields.Datetime.now()
        default_landing = self._uia_default_landing(target)
        if target.share and (landing_url or '').startswith(('/odoo', '/web')):
            landing_url = default_landing  # a portal user cannot open backend pages
        vals = {
            'impersonator_id': impersonator.id,
            'target_id': target.id,
            'target_share': target.share,
            'company_id': self.env.company.id,
            'policy_id': info['policy'].id,
            'consent_id': consent.id,
            'reason_category': reason_category or 'support',
            'reason': reason,
            'reference': reference or False,
            'read_only': read_only,
            'start_date': now,
            'planned_end_date': now + timedelta(minutes=info['time_limit']),
            'landing_url': safe_local_url(landing_url, default_landing),
        }
        if request:
            httpreq = request.httprequest
            vals.update({
                'ip_address': httpreq.remote_addr,
                'user_agent': (httpreq.user_agent.string or '')[:250],
                'session_hash': hashlib.sha256(request.session.sid.encode()).hexdigest(),
            })
        log = self.sudo().create(vals)
        if consent:
            consent.write({'state': 'used', 'session_id': log.id})
        log._uia_note_on_target(_('%(who)s logged in as this user. Reason: %(reason)s',
                                  who=impersonator.name, reason=reason))
        log._uia_notify_start(force_target=(mode == 'notify'))
        _logger.info('Impersonation started: %s (uid %s) as %s (uid %s), session %s',
                     impersonator.login, impersonator.id, target.login, target.id, log.id)
        if request:
            log._uia_switch_to_target(safe_local_url(return_url, '/odoo'))
        return log

    @api.model
    def _uia_default_landing(self, target):
        if not target.share:
            return '/odoo'
        portal = self.env['ir.module.module'].sudo().search_count([('name', '=', 'portal'), ('state', '=', 'installed')])
        return '/my' if portal else '/web/login_successful'

    def _uia_switch_to_target(self, return_url):
        self.ensure_one()
        real = self.env.user
        now = time.time()
        imp = {
            'log_id': self.id,
            'real_uid': real.id,
            'real_name': real.name,
            'target_uid': self.target_id.id,
            'started': now,
            'expires': now + (self.planned_end_date - self.start_date).total_seconds(),
            'last_seen': now,
            'read_only': self.read_only,
            'extended': False,
            'return_url': return_url,
            'real_fp': _fingerprint(real),
            'cids': request.cookies.get('cids'),
        }
        # the target's account must never inherit the impersonator's recent password check
        imp['identity_check'] = request.session.pop('identity-check-last', None)
        switch_session_user(self.env, self.target_id)
        request.session[SESSION_KEY] = imp
        request.future_response.set_cookie('cids', max_age=0)

    def _uia_end(self, reason, ended_by=None):
        for rec in self.sudo().filtered(lambda s: s.state == 'active'):
            rec.write({
                'state': 'ended',
                'end_date': fields.Datetime.now(),
                'end_reason': reason,
                'ended_by_id': ended_by.id if ended_by else False,
            })
            rec._uia_note_on_target(_('%(who)s returned to their own account (%(why)s, %(minutes)s min).',
                                      who=rec.impersonator_id.name,
                                      why=dict(rec._fields['end_reason']._description_selection(rec.env))[reason],
                                      minutes=rec.duration))
            if get_config(rec.env)['send_summary']:
                rec._uia_send(rec.env.ref('user_impersonation_audit.mail_template_session_summary'),
                              rec.target_id.partner_id)
            _logger.info('Impersonation ended: session %s (%s)', rec.id, reason)

    @api.model
    def _uia_end_all_on_uninstall(self):
        """Uninstall: end every active session and log its browser out (nothing would send it back to
        the real user once the app is gone), then drop the trail so demo users can be removed."""
        active = self.sudo().search([('state', '=', 'active')])
        identifiers = [i for i in active.mapped('session_identifier') if i]
        active._uia_end('forced')
        if identifiers:
            session_store().delete_from_identifiers(identifiers)
        self.env['user.impersonation.consent'].sudo().search([]).unlink()
        self.sudo().with_context(active_test=False).search([]).unlink()

    def action_force_end(self):
        if not self.env.user.has_group(GROUP_MANAGER):
            raise AccessError(_('Only impersonation managers can end a session.'))
        self.check_access('read')
        self._uia_end('forced', ended_by=self.env.user)
        return True

    # ------------------------------------------------------------------ chatter / mail
    def _uia_note_on_target(self, text):
        """Silent internal note on the target's contact: no follower notification, no inbox ping."""
        self.ensure_one()
        # posted as the superuser: the request may still run as the (read-only) impersonated user
        partner = self.target_id.partner_id.with_user(SUPERUSER_ID).sudo()
        partner.with_context(mail_create_nosubscribe=True, mail_post_autofollow=False).message_post(
            body=escape(text), message_type='comment', subtype_xmlid='mail.mt_note',
            author_id=self.impersonator_id.partner_id.id)

    def _uia_notify_start(self, force_target=False):
        conf = get_config(self.env)
        template = self.env.ref('user_impersonation_audit.mail_template_session_started')
        if conf['notify_target'] or force_target:
            self._uia_send(template, self.target_id.partner_id)
        if conf['notify_managers']:
            managers = self.env.ref(GROUP_MANAGER).sudo().all_user_ids.filtered(
                lambda u: u.active and u.email and not u.share and u != self.impersonator_id
                and self.company_id in u.company_ids)
            self._uia_send(template, managers.partner_id)

    def _uia_send(self, template, partners):
        partners = partners.filtered('email')
        if partners:
            template.sudo().send_mail(self.id, email_values={'recipient_ids': [(4, p.id) for p in partners]})

    def uia_changed_activities(self):
        return self.activity_ids.filtered(lambda a: a.operation in ('create', 'write', 'unlink'))

    # ------------------------------------------------------------------ cron
    @api.model
    def _cron_housekeeping(self):
        conf = get_config(self.env)
        now = fields.Datetime.now()
        stale = self.sudo().search([('state', '=', 'active'), ('planned_end_date', '<', now - timedelta(minutes=5))])
        stale._uia_end('expired')
        consent = self.env['user.impersonation.consent'].sudo()
        consent.search([('state', '=', 'pending'), ('create_date', '<', now - timedelta(hours=24))]).write(
            {'state': 'expired'})
        consent.search([('state', '=', 'approved'), ('valid_until', '<', now)]).write({'state': 'expired'})
        if conf['retention_days'] > 0:
            limit = now - timedelta(days=conf['retention_days'])
            old = self.sudo().search([('state', '=', 'ended'), ('end_date', '<', limit)])
            consent.search([('create_date', '<', limit), ('state', '!=', 'pending')]).unlink()
            if old:
                _logger.info('Impersonation: purging %s sessions older than %s days', len(old), conf['retention_days'])
                old.unlink()

    # ------------------------------------------------------------------ demo
    @api.model
    def _uia_demo_create(self):
        """Fictional ended sessions with tracked activity, for the demo database."""
        admin = self.env.ref('base.user_admin')
        marc = self.env.ref('base.user_demo')
        portal = self.env.ref('base.demo_user0', raise_if_not_found=False)
        agent = self.env.ref('user_impersonation_audit.demo_user_agent')
        company = admin.company_id
        now = fields.Datetime.now()
        Activity = self.env['user.impersonation.activity'].sudo()
        specs = [
            (admin, marc, 'support', 'Marc cannot see the Q3 price list in the quotation form.', 'TCK-1042', False, 3, 21, 'manual'),
            (admin, marc, 'access_test', 'Check that new sales rules hide other teams’ pipelines.', 'CHG-77', True, 1, 9, 'manual'),
            (agent, portal, 'support', 'Customer reports the invoice download button does nothing.', 'TCK-1057', True, 0, 15, 'timeout'),
            (admin, marc, 'training', 'Walk through the expense flow for the onboarding guide.', False, False, 6, 34, 'idle'),
            (agent, portal, 'support', 'Portal address change does not save.', 'TCK-1063', True, 2, 6, 'manual'),
        ]
        sessions = self.browse()
        for i, (who, whom, cat, reason, ref, ro, days, minutes, end_reason) in enumerate(specs):
            if not whom:
                continue
            start = now - timedelta(days=days, hours=2 + i)
            sessions |= self.sudo().create({
                'impersonator_id': who.id, 'target_id': whom.id, 'target_share': whom.share,
                'company_id': company.id, 'reason_category': cat, 'reason': reason, 'reference': ref,
                'read_only': ro, 'start_date': start, 'planned_end_date': start + timedelta(minutes=60 if who == admin else 15),
                'end_date': start + timedelta(minutes=minutes), 'state': 'ended', 'end_reason': end_reason,
                'ip_address': '10.0.%s.%s' % (4 + i, 20 + i * 7),
                'user_agent': 'Mozilla/5.0 (X11; Linux x86_64) Chrome/140.0 Safari/537.36',
                'session_hash': hashlib.sha256(('demo-%s' % i).encode()).hexdigest(),
                'landing_url': '/my' if whom.share else '/odoo',
            })
        first = sessions[:1]
        if first:
            partner = self.env.ref('base.res_partner_4', raise_if_not_found=False) or marc.partner_id
            t0 = first.start_date
            Activity.create([
                {'session_id': first.id, 'date': t0 + timedelta(minutes=1), 'operation': 'action',
                 'summary': 'Contacts', 'model': 'res.partner'},
                {'session_id': first.id, 'date': t0 + timedelta(minutes=4), 'operation': 'write',
                 'model': 'res.partner', 'model_description': 'Contact', 'res_id': partner.id,
                 'record_name': partner.display_name, 'summary': 'Phone, Website',
                 'change_ids': [(0, 0, {'field_name': 'phone', 'field_description': 'Phone',
                                        'old_value': '+1 555-0100', 'new_value': '+1 555-0142'}),
                                (0, 0, {'field_name': 'website', 'field_description': 'Website',
                                        'old_value': '', 'new_value': 'https://example.com'})]},
                {'session_id': first.id, 'date': t0 + timedelta(minutes=9), 'operation': 'message',
                 'model': 'res.partner', 'model_description': 'Contact', 'res_id': partner.id,
                 'record_name': partner.display_name, 'summary': 'Message posted as the real user'},
            ])
        olivia = self.env.ref('user_impersonation_audit.demo_user_olivia')
        self.env['user.impersonation.consent'].sudo().create({
            'requester_id': admin.id, 'target_id': olivia.id, 'company_id': company.id,
            'reason': 'Check the new approval menu from her point of view.', 'reference': 'CHG-80',
            'state': 'refused', 'decision_date': now - timedelta(days=2), 'access_token': 'demo-token-refused'})
        return sessions
