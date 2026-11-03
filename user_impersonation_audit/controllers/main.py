import time
from datetime import timedelta

from werkzeug.exceptions import NotFound

from odoo import _, http
from odoo.exceptions import AccessError, UserError
from odoo.http import request
from odoo.tools.misc import consteq

from odoo.addons.web.controllers.action import Action
from odoo.addons.web.controllers.session import Session

from ..models.common import SESSION_KEY, current_impersonation, get_config, separate_env
from ..models.impersonation_session import restore_real_user


class ImpersonationController(http.Controller):

    # website=True: pages rendered with web.frontend_layout need the website context when installed
    @http.route('/impersonation/return', type='http', auth='user', methods=['GET'], website=True)
    def impersonation_return_confirm(self, **kwargs):
        """A plain link (bookmark, prefetch, another site) never switches accounts: it shows a button."""
        imp = current_impersonation()
        if not imp:
            return request.redirect('/odoo', 303)
        return request.render('user_impersonation_audit.return_confirm', {'imp': imp})

    @http.route('/impersonation/return', type='http', auth='user', methods=['POST'], website=True)
    def impersonation_return(self, **kwargs):
        imp = current_impersonation()
        if not imp:
            return request.redirect('/odoo', 303)
        reason = 'timeout' if time.time() >= imp['expires'] else 'manual'
        request.env['user.impersonation.session'].sudo().browse(imp['log_id'])._uia_end(reason)
        restored = restore_real_user(request.env, imp)
        return request.redirect((imp.get('return_url') or '/odoo') if restored else '/web/login', 303)

    @http.route('/impersonation/extend', type='jsonrpc', auth='user')
    def impersonation_extend(self, reason=''):
        imp = current_impersonation()
        if not imp:
            raise UserError(_('You are not logged in as another user.'))
        conf = get_config(request.env)
        log = request.env['user.impersonation.session'].sudo().browse(imp['log_id'])
        if not conf['allow_extension'] or imp.get('extended') or log.state != 'active':
            raise UserError(_('This session cannot be extended.'))
        reason = (reason or '').strip()
        if len(reason) < conf['min_reason_length']:
            raise UserError(_('Please give a reason of at least %s characters.', conf['min_reason_length']))
        max_end = imp['started'] + conf['max_time_limit'] * 60
        new_end = min(imp['expires'] + conf['extension_minutes'] * 60, max_end)
        if new_end <= imp['expires']:
            raise UserError(_('The session already reached the hard maximum.'))
        log.write({
            'extended': True,
            'extension_reason': reason,
            'planned_end_date': log.start_date + timedelta(seconds=new_end - imp['started']),
        })
        request.session[SESSION_KEY] = dict(imp, expires=new_end, extended=True)
        return {'remaining': int(new_end - time.time())}

    @http.route('/impersonation/consent/<int:consent_id>/<string:decision>', type='http', auth='user',
                methods=['GET'], website=True)
    def impersonation_consent(self, consent_id, decision, token='', **kwargs):
        consent = request.env['user.impersonation.consent'].sudo().browse(consent_id).exists()
        if decision not in ('approve', 'refuse') or not consent or not token \
                or not consteq(consent.access_token or '', token):
            raise NotFound()
        error = False
        try:
            consent._uia_decide(decision, request.env.user)
        except (UserError, AccessError) as e:
            error = e.args[0]
        return request.render('user_impersonation_audit.consent_result', {
            'consent': consent, 'decision': decision, 'error': error,
        })


class ImpersonationSession(Session):

    @http.route()
    def logout(self, redirect='/odoo'):
        imp = request.session.get(SESSION_KEY)
        if imp:
            with separate_env(request.env) as env:
                env['user.impersonation.session'].browse(imp['log_id'])._uia_end('logout')
        return super().logout(redirect=redirect)


class ImpersonationAction(Action):

    @http.route()
    def load(self, action_id, context=None):
        result = super().load(action_id, context=context)
        imp = current_impersonation()
        if imp and result and get_config(request.env)['track_actions']:
            # the list that opens next is the same screen: do not record it twice
            request.session[SESSION_KEY] = dict(imp, last_view=[result.get('res_model') or False, False])
            with separate_env(request.env) as env:
                env['user.impersonation.activity'].create({
                    'session_id': imp['log_id'], 'operation': 'action',
                    'summary': (result.get('display_name') or result.get('name') or '')[:250],
                    'model': result.get('res_model') or False,
                    'model_description': result.get('res_model') and env['ir.model']._get(result['res_model']).name,
                })
        return result
