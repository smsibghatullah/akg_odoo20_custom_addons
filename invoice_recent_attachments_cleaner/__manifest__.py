{
    'name': 'Invoice Attachment Cleaner',
    'version': '20.0.1.0.0',
    'author': 'DSM',
    'license': 'LGPL-3',
    'category': 'Accounting',
    'website': 'https://www.dsmpk.com',
    'summary': 'Clean old invoice attachments, keep only the last 3 months.',
    'description': """
This module automatically removes old attachments from customer invoices,
keeping only those created in the last 3 months. It helps reduce storage usage 
by cleaning up outdated invoice documents.

Key Features:
- Automatically detect and remove old invoice attachments.
- Only keeps attachments from the last 3 months.
- Supports account.move (Customer Invoices) model.
""",
    'depends': ['base', 'mail', 'web', 'account'],
    'data': [
        'data/ir_cron_attachment_cleaner.xml',
    ],
    'assets': {},
    'installable': True,
    'application': True,
    'support': 'dynamicsolutionmaker@gmail.com',
}
