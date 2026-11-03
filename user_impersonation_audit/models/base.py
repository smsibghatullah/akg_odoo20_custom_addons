"""ORM hooks active only inside an impersonated browser session:
read-only mode blocks create/write/unlink, otherwise each change is recorded field by field;
the lists and records opened are recorded too."""
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.http import request

from .common import (
    PROTECTED_USER_FIELDS, SESSION_KEY, current_impersonation, format_value, get_config, is_implicit_write,
    is_print_flag, is_technical_model,
    separate_env,
)

MAX_TRACKED_RECORDS = 50
MAX_TRACKED_FIELDS = 40


class Base(models.AbstractModel):
    _inherit = 'base'

    def _uia_guard(self, operation, vals=None):
        """Return the impersonation data when this call must be recorded, None otherwise.
        Raise when the session is read-only or the call touches credentials."""
        imp = current_impersonation()
        if not imp or self.env.uid != imp['target_uid']:
            return None
        if self._name == 'res.users' and vals and PROTECTED_USER_FIELDS.intersection(vals):
            raise UserError(_('Passwords, security keys and consent settings cannot be changed while you are logged in as another user.'))
        if is_technical_model(self) or self.env.su and is_implicit_write(self, vals) or is_print_flag(self, vals):
            return None
        # Sudo writes made on the user's behalf (portal address form, website cart...) are blocked
        # in read-only mode and recorded otherwise, exactly like the user's own writes.
        if imp.get('read_only'):
            raise UserError(_('Read-only session: changes are blocked while you are logged in as another user. '
                              'Return to your account to make changes.'))
        if not get_config(self.env)['track_changes']:
            return None
        return imp

    def _uia_log(self, imp, operation, records_info):
        Activity = self.env['user.impersonation.activity'].sudo()
        description = self.env['ir.model']._get(self._name).name or self._name
        now = fields.Datetime.now()
        vals_list = []
        for res_id, name, changes in records_info[:MAX_TRACKED_RECORDS]:
            vals_list.append({
                'session_id': imp['log_id'], 'date': now, 'operation': operation,
                'model': self._name, 'model_description': description, 'res_id': res_id,
                'record_name': (name or '')[:250],
                'summary': ', '.join(c['field_description'] for c in changes)[:250] if changes else description,
                'change_ids': [(0, 0, c) for c in changes],
            })
        if vals_list:
            Activity.create(vals_list)

    def _uia_snapshot(self, fnames):
        return {rec.id: {f: format_value(rec, f) for f in fnames} for rec in self.sudo()[:MAX_TRACKED_RECORDS]}

    def _uia_log_view(self, res_id=False):
        """Record the list or record the impersonated session looks at (where the impersonator looked).
        The browser restores screens from its own cache, so this is logged on the data read itself."""
        imp = current_impersonation()
        # only plain reads: after a save the change itself is already recorded
        if not imp or self.env.uid != imp['target_uid'] or not self.env.cr.readonly \
                or is_technical_model(self) or self.env.context.get('uia_view_logged'):
            return
        key = [self._name, res_id]
        if imp.get('last_view') == key or not get_config(self.env)['track_actions']:
            return
        request.session[SESSION_KEY] = dict(imp, last_view=key)
        record_name = self.sudo().browse(res_id).display_name if res_id else False
        with separate_env(self.env) as env:
            description = env['ir.model']._get(self._name).name or self._name
            env['user.impersonation.activity'].create({
                'session_id': imp['log_id'], 'operation': 'action', 'model': self._name,
                'model_description': description, 'res_id': res_id or 0,
                'record_name': (record_name or '')[:250] or False,
                'summary': (_('%s (record)', description) if res_id else _('%s (list)', description))[:250],
            })

    @api.model
    @api.readonly
    def web_search_read(self, domain, specification, offset=0, limit=None, order=None, count_limit=None):
        self._uia_log_view()
        return super(Base, self.with_context(uia_view_logged=True)).web_search_read(
            domain, specification, offset=offset, limit=limit, order=order, count_limit=count_limit)

    @api.readonly
    def web_read(self, specification):
        if len(self) == 1:
            self._uia_log_view(self.id)
        return super().web_read(specification)

    @api.model_create_multi
    def create(self, vals_list):
        imp = self._uia_guard('create', vals_list[0] if vals_list else None)
        records = super().create(vals_list)
        if imp:
            self._uia_log(imp, 'create', [(r.id, r.sudo().display_name, []) for r in records])
        return records

    def write(self, vals):
        imp = self._uia_guard('write', vals)
        if not imp or not self:
            return super().write(vals)
        fnames = [f for f in vals if f in self._fields and self._fields[f].store
                  and self._fields[f].type != 'binary'][:MAX_TRACKED_FIELDS]
        before = self._uia_snapshot(fnames)
        res = super().write(vals)
        after = self._uia_snapshot(fnames)
        info = []
        for rec in self.sudo()[:MAX_TRACKED_RECORDS]:
            changes = [{
                'field_name': f, 'field_description': self._fields[f]._description_string(self.env),
                'old_value': before[rec.id][f], 'new_value': after[rec.id][f],
            } for f in fnames if before[rec.id][f] != after[rec.id][f]]
            if changes:
                info.append((rec.id, rec.display_name, changes))
        self._uia_log(imp, 'write', info)
        return res

    def unlink(self):
        imp = self._uia_guard('unlink')
        if not imp:
            return super().unlink()
        info = [(r.id, r.display_name, []) for r in self.sudo()]
        res = super().unlink()
        self._uia_log(imp, 'unlink', info)
        return res
