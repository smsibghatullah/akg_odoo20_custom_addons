"""Shared helpers: settings, the impersonation data kept in the HTTP session, value formatting."""
import contextlib

from odoo import SUPERUSER_ID, api
from odoo.http import request
from odoo.tools import html2plaintext

PARAM_PREFIX = 'user_impersonation_audit.'
GROUP_USER = 'user_impersonation_audit.group_impersonation_user'
GROUP_MANAGER = 'user_impersonation_audit.group_impersonation_manager'
SESSION_KEY = 'impersonation'

# key: (type, default). Stored as plain strings in ir.config_parameter so that False / 0 survive.
PARAMS = {
    'time_limit': ('int', 60),
    'max_time_limit': ('int', 120),
    'idle_timeout': ('int', 30),
    'min_reason_length': ('int', 10),
    'read_only_default': ('bool', False),
    'allow_admin_targets': ('bool', False),
    'require_password': ('bool', True),
    'default_consent': ('str', 'never'),
    'notify_target': ('bool', False),
    'notify_managers': ('bool', False),
    'send_summary': ('bool', False),
    'track_changes': ('bool', True),
    'track_actions': ('bool', True),
    'allow_extension': ('bool', True),
    'extension_minutes': ('int', 30),
    'retention_days': ('int', 365),
    'ip_allowlist': ('str', ''),
    'hours_from': ('float', 0.0),
    'hours_to': ('float', 0.0),
}

_CAST = {'int': int, 'float': float, 'str': str, 'bool': lambda v: v == 'True'}

# Models never tracked nor blocked: framework plumbing written implicitly by the web client.
TECHNICAL_PREFIXES = (
    'ir.', 'bus.', 'base.', 'web_tour.', 'res.users.settings', 'res.device', 'res.users.log',
    'res.users.identitycheck', 'mail.presence', 'mail.notification', 'mail.link.preview',
    'mail.message.reaction', 'discuss.channel.member', 'discuss.channel.rtc', 'mail.guest',
    'user.impersonation.',
)
TECHNICAL_EXCEPTIONS = ('ir.attachment', 'ir.filters')  # saved filters are the user's own data
# Credentials and consent settings are never changed through an impersonated session.
PROTECTED_USER_FIELDS = frozenset({'password', 'new_password', 'totp_secret', 'api_key_ids',
                                   'impersonation_grant_until', 'impersonation_consent', 'impersonation_protected'})


def get_config(env):
    icp = env['ir.config_parameter'].sudo()
    conf = {}
    for key, (typ, default) in PARAMS.items():
        raw = icp.get_str(PARAM_PREFIX + key, None)
        if raw is None:
            conf[key] = default
            continue
        try:
            conf[key] = _CAST[typ](raw)
        except ValueError:
            conf[key] = default
    return conf


def set_config(env, values):
    icp = env['ir.config_parameter'].sudo()
    for key, value in values.items():
        typ = PARAMS[key][0]
        if typ == 'bool':
            value = 'True' if value else 'False'
        elif typ == 'str':
            value = (value or '').strip()
        else:
            value = str(value or 0)
        icp.set_str(PARAM_PREFIX + key, value)


def current_impersonation():
    """Impersonation data of the current HTTP session, only while the session runs as the target."""
    if not request:
        return None
    session = getattr(request, 'session', None)
    imp = session.get(SESSION_KEY) if session is not None else None
    if imp and session.uid == imp.get('target_uid'):
        return imp
    return None


def is_technical_model(model):
    name = model._name
    if model._transient or model._abstract:
        return True
    if name in TECHNICAL_EXCEPTIONS:
        return False
    return name.startswith(TECHNICAL_PREFIXES)


# Sudo writes the framework makes by itself while a user only browses: chatter/discuss plumbing,
# report and asset attachments, website visitor tracking, portal access tokens, OdooBot onboarding.
# ponytail: prefix list, extend it when a module does sudo bookkeeping writes on page views.
IMPLICIT_SUDO_PREFIXES = ('mail.', 'discuss.', 'ir.attachment', 'website.visitor', 'website.track')
IMPLICIT_SUDO_FIELDS = frozenset({'access_token', 'message_main_attachment_id', 'odoobot_state'})
# Bookkeeping flags written as the user when a document is merely printed (allowed even read-only).
# ponytail: per-model list, extend it when another report marks its records on print.
PRINT_FLAGS = {'stock.picking': frozenset({'printed'})}


def is_implicit_write(model, vals=None):
    return model._name.startswith(IMPLICIT_SUDO_PREFIXES) or bool(vals) and IMPLICIT_SUDO_FIELDS.issuperset(vals)


def is_print_flag(model, vals=None):
    return bool(vals) and model._name in PRINT_FLAGS and PRINT_FLAGS[model._name].issuperset(vals)


def format_value(record, fname):
    field = record._fields[fname]
    value = record[fname]
    if field.type in ('many2one', 'many2many', 'one2many'):
        text = ', '.join(value.sudo().mapped('display_name'))
    elif field.type == 'selection':
        text = dict(field._description_selection(record.env)).get(value, value) or ''
    elif field.type == 'html':
        text = html2plaintext(value or '')
    elif field.type == 'boolean':
        text = str(bool(value))
    elif value is False or value is None:
        text = ''
    else:
        text = str(value)
    return text[:1000]


@contextlib.contextmanager
def separate_env(env):
    """Superuser env whose writes are committed on exit, even if the request then ends with an
    error response (never committed by the framework). A read-only request cursor is rolled back
    and a read/write cursor is opened (same pattern as res.device.log); a read/write request
    cursor is committed in place."""
    if env.cr.readonly:
        env.cr.rollback()
        with env.registry.cursor(readonly=False) as cr:
            yield api.Environment(cr, SUPERUSER_ID, {})
    else:
        yield api.Environment(env.cr, SUPERUSER_ID, {})
        env.cr.commit()

