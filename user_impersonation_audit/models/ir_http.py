import logging
import time

import werkzeug.exceptions

from odoo import api, models
from odoo.http import request
from odoo.http.dispatcher import serialize_exception
from odoo.http.session import STORED_SESSION_BYTES, SessionExpiredException

from .common import GROUP_USER, SESSION_KEY, get_config, separate_env
from .impersonation_session import restore_real_user

_logger = logging.getLogger(__name__)

LAST_SEEN_GRANULARITY = 15  # seconds: the session file is rewritten at most every 15 s


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _authenticate(cls, endpoint):
        super()._authenticate(endpoint)
        imp = request.session.get(SESSION_KEY)
        if imp and request.httprequest.path != '/impersonation/return':
            cls._uia_enforce(imp)

    @classmethod
    def _uia_enforce(cls, imp):
        """Server-side safety net of every impersonated request: time limit, idle timeout and
        sessions ended by a manager send the browser back to the real user."""
        session = request.session
        if session.uid != imp.get('target_uid'):
            session.pop(SESSION_KEY)  # logged out / logged in again meanwhile: stale data
            return
        now = time.time()
        conf = get_config(request.env)
        request.env.cr.execute('SELECT state FROM user_impersonation_session WHERE id = %s', [imp['log_id']])
        row = request.env.cr.fetchone()
        reason = None
        if not row or row[0] != 'active':
            reason = 'forced'
        elif now >= imp['expires']:
            reason = 'timeout'
        elif conf['idle_timeout'] and now - imp['last_seen'] > conf['idle_timeout'] * 60:
            reason = 'idle'
        if not reason:
            identifier = session.sid[:STORED_SESSION_BYTES]
            if imp.get('sid') != identifier:  # first request after the switch (the login rotated the id)
                with separate_env(request.env) as env:
                    env['user.impersonation.session'].browse(imp['log_id']).session_identifier = identifier
                session[SESSION_KEY] = dict(imp, sid=identifier, last_seen=now)
            elif now - imp['last_seen'] > LAST_SEEN_GRANULARITY:
                session[SESSION_KEY] = dict(imp, last_seen=now)
            return
        if row and row[0] == 'active':
            with separate_env(request.env) as env:
                env['user.impersonation.session'].browse(imp['log_id'])._uia_end(reason)
        _logger.info('Impersonation session %s ended on request (%s)', imp['log_id'], reason)
        restored = restore_real_user(request.env, imp)
        target = imp.get('return_url') if restored else '/web/login'
        if request.dispatcher.routing_type == 'jsonrpc':
            error = {'code': 100, 'message': 'Odoo Session Expired',
                     'data': serialize_exception(SessionExpiredException('Impersonation ended'))}
            response = request.make_json_response({'jsonrpc': '2.0', 'id': None, 'error': error})
        else:
            response = request.redirect(target or '/odoo', 303)
        werkzeug.exceptions.abort(response)

    def session_info(self):
        info = super().session_info()
        imp = request.session.get(SESSION_KEY)
        banner = self.uia_banner_info()
        if banner:
            conf = get_config(self.env)
            max_end = imp['started'] + conf['max_time_limit'] * 60
            info['impersonation'] = dict(
                banner,
                can_extend=conf['allow_extension'] and not imp.get('extended') and imp['expires'] < max_end,
                min_reason_length=conf['min_reason_length'],
            )
        info['impersonation_can_start'] = bool(not imp and request.session.uid
                                               and self.env.user.has_group(GROUP_USER))
        return info

    @api.model
    def uia_banner_info(self):
        """Data for the server-rendered portal/website banner (only for the session's own impersonation)."""
        imp = request.session.get(SESSION_KEY) if request else None
        if not imp or request.session.uid != imp.get('target_uid'):
            return None
        return {
            'real_name': imp['real_name'],
            'target_name': self.env.user.name,
            'read_only': imp.get('read_only'),
            'remaining': max(0, int(imp['expires'] - time.time())),
        }
