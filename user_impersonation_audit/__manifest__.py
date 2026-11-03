{
    'name': 'Admin Login As User: Impersonate Users Safely with Audit Trail',
    'version': '20.0.1.0.0',
    'category': 'Administration/Administration',
    'summary': 'Log in as another user (internal or portal) to reproduce issues: mandatory reason, time limit with automatic return, read-only mode, who-may-impersonate-whom policies, target consent, field-level change audit, banner with return button. Free. Keywords: login as, login as user, login as any user, log in as, impersonate, impersonation, impersonate users, switch user, become user, portal user login, audit trail.',
    'description': """
Login As User with Audit Trail
==============================

Authorised staff log in as another user to reproduce an issue, with a complete audit trail.

* Start from the user form, the Users list (Action menu) or a searchable picker in the top bar.
* Mandatory reason with category and reference, shown target companies and groups, confirmation.
* Dedicated group, empty by default. Every check runs on the server.
* Hard blocks: superuser, self, archived, public user, nested sessions, users with more rights,
  administrators (unless allowed), protected users and groups, other companies.
* Policies: members of group A may impersonate users of groups B in companies C, with their own
  time limit and forced read-only.
* Read-only mode: create, write and delete are refused while impersonating.
* Time limit with automatic return, idle timeout, one extension with a new reason, hard maximum.
* Banner on backend and portal pages with live countdown and a Return to my account button.
* Target consent per user: never ask, notify only or require approval. Self-service access grant.
* Optional password re-entry before starting, IP allowlist and allowed hours.
* Append-only session log with IP, browser, duration and end reason; field-level change audit,
  opened actions, messages posted as the real user; graph and pivot views; force end.
* Silent chatter note on the target, optional emails to the target and managers, end-of-session
  summary, retention with scheduled purge.
""",
    'author': 'Viyug Infotech',
    'support': 'support@viyuginfotech.com',
    'website': 'https://viyuginfotech.com',
    'license': 'LGPL-3',
    'depends': ['base', 'web', 'mail'],
    'data': [
        'security/security.xml',
        'security/ir.access.csv',
        'data/ir_cron.xml',
        'data/mail_templates.xml',
        'views/session_views.xml',
        'views/policy_views.xml',
        'views/consent_views.xml',
        'views/wizard_views.xml',
        'views/res_users_views.xml',
        'views/res_config_settings_views.xml',
        'views/templates.xml',
        'views/menus.xml',
    ],
    'demo': ['demo/demo.xml'],
    'assets': {
        'web.assets_backend': [
            'user_impersonation_audit/static/src/backend/**/*',
        ],
        'web.assets_frontend': [
            'user_impersonation_audit/static/src/backend/impersonation.scss',
            'user_impersonation_audit/static/src/backend/impersonation_utils.js',
            'user_impersonation_audit/static/src/frontend/**/*',
        ],
    },
    'images': ['static/description/cover.gif'],
    'uninstall_hook': 'uninstall_hook',
    'installable': True,
    'application': False,
}
