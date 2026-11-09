{
    'name': 'Journal Entry - Allow All Account Types',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Remove account type restriction on Account field of journal entry lines',
    'description': """
Removes the domain on the Account field of Journal Entry lines that hides
Bank and Cash, Receivable, Payable and Off-Balance accounts, so all accounts
of the company (e.g. Petty Cash) can be selected like in Odoo 16.
    """,
    'author': 'AKG',
    'depends': ['account'],
    'data': [
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
