# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.
{
    'name': 'Credit Limit Approval',
    'version': '20.0.0.0',
    'summary': """
    Odoo Credit Limit Approval for customer credit limit, blocking sales order credit, sales manager approval credit, account manager credit. Warn or block sale confirmation when the customer exceeds credit, with manager approval.
    """,
    'description': """
    Credit Limit Approval delivers customer credit limit for Odoo. Warn or block sale confirmation when the customer exceeds credit, with manager approval. Puts credit control on the order, not only on invoices.

Set up the rules once and apply them where your team works every day. Typical use cases include wholesale credit, overdue AR, exception quotes.

Key features include sales manager approval credit, account manager credit, credit limit warning, approval on Odoo sales orders.

It supports business workflows such as credit control, order release.

Credit Limit Approval is suitable for organizations that need reliable customer credit limit without building a custom module for every exception.

The module is ideal for distribution, manufacturing, B2B.

Strengthen your Odoo operations with Credit Limit Approval, covering customer credit limit, block sales order credit.
    """,
    'author': "TechUltra Solutions Private Limited",
    'company': 'TechUltra Solutions Private Limited',
    'website': "https://www.techultrasolutions.com/",
    'category': 'Sales',
    'depends': ['sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'data/credit_limit_approval_mail.xml',
        'wizard/warning_wizard.xml',
        'views/res_partner.xml',
        'views/sale_order.xml',
    ],
    'images': [
        'static/description/main_screen.gif',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'OPL-1',
}
