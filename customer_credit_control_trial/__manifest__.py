# -*- coding: utf-8 -*-
{
    'name': "Customer Credit Control - Trial",
    'version': '20.0.1.0.0',
    'depends': ['sale_management'],
    'author': "Aakash Infosoft",
    'website': "https://aakash.com",
    'category': 'Sale Management',
    'summary': "Trial Version of Customer Credit Control",
    'license': "AGPL-3",
    'description': """
    This app is a trial version of our "Customer Credit Control" Applicaiton. Only limited features are enabled in
    this application but you can see all the configurations, So you have an idea how our "Customer Credit Control"
    Application works. But only limited configurations can be done, Others are just visible to display what we
    provide in our Main Application.
    
    **Note : This is a trial version of our application "Customer Credit Control". If you are buying it, remove this
    application before installing it.**
    """,
    'data': [
        "wizard/warning_wizard_views.xml",
        "wizard/res_config_settings_views.xml",
        "views/res_partner_views.xml",
        "security/ir.access.csv"
    ],
    'images': [
        'static/description/ccc_trial.jpg',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
