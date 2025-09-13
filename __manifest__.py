{
    'name': 'Support Center',
    'version': '1.0.0',
    'category': 'Services',
    'summary': 'Support appointment scheduling and management system',
    'description': """
Support Center Module

This module provides a comprehensive appointment scheduling system for support teams.
Features include:
- Role-based calendar views for managers and technicians
- Integration with Helpdesk module
- Automated email notifications
- External API for appointment booking
- Color-coded appointment status tracking
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'base',
        'helpdesk',
        'mail',
        'web',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequences.xml',
        'data/cron_jobs.xml',
        'data/automation_rules.xml',
        'views/appointment_menus.xml',
        'views/appointment_views.xml',
        'views/appointment_wizard_views.xml',
        'data/email_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'support_center/static/src/css/appointment_calendar.css',
            'support_center/static/src/js/appointment_calendar.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}