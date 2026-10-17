{
    'name': "custom_attendance",

    'summary': """
        A comprehensive attendance management module integrating ZK biometric devices with Odoo's HR system.
    """,

    'description': """
        The custom_attendance module is designed to seamlessly connect ZK biometric attendance machines with Odoo's HR attendance system. It automates the process of capturing employee attendance data from ZK devices and updates it in real time within the Odoo environment.

        Key Features:
        - Integration with ZK biometric devices to track employee attendance.
        - Real-time syncing of attendance data with Odoo's HR module.
        - Automated data fetching from ZK devices and error handling.
        - Detailed attendance reports and insights.
        - Streamlined attendance management for payroll and leave tracking.

        This module enhances attendance accuracy and reduces manual data entry efforts, making attendance management more efficient for organizations.
    """,

    'author': "Dynamic Solution Maker",
    'website': "https://www.dsmpk.com",

    'category': 'HR',
    'version': '20.0.1.0.0',

    'depends': ['base','hr','hr_attendance', 'account'],

    'data': [
        'views/views.xml',
        'views/templates.xml',
    ],
    'demo': [
        'demo/demo.xml',
    ],
}
