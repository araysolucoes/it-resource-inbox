# -*- coding: utf-8 -*-
{
    'name': 'Email Inbox',
    'version': '14.0.1.7.0',
    'category': 'Productivity',
    'summary': 'Per-provider accounts, plain text or HTML sending and templates with variables',
    'description': """
Email Inbox
===========

Each account picks its provider and the system fills in SMTP and POP3.
Other modules send through send_for_record or email.template.send
and read the conversation with thread_for.
    """,
    'author': 'Odoo Native',
    'license': 'LGPL-3',
    'depends': ['base', 'web', 'mail', 'fetchmail'],
    'data': [
        'security/email_inbox_security.xml',
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'views/email_account_views.xml',
        'views/email_message_views.xml',
        'views/email_template_views.xml',
        'wizard/email_compose_views.xml',
        'views/menus.xml',
        'views/assets.xml',
    ],
    'installable': True,
    'application': True,
}
