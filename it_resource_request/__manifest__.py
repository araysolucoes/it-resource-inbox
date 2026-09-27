# -*- coding: utf-8 -*-
# Odoo reads this file with ast.literal_eval, so it must contain only the
# dictionary below: a module docstring here would break module loading.
{
    'name': 'IT resource requests',
    'version': '14.0.3.8.0',
    'category': 'Human Resources',
    'summary': 'Requests for physical and virtual items, without the Odoo inventory',
    'description': """
IT resource requests
====================

Own catalog of equipment, VPN, licenses and other items.
Other modules open a request through it.resource.request.request_for and the item code.
    """,
    'author': 'Odoo Native',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'web', 'email_inbox'],
    'data': [
        'security/it_resource_security.xml',
        'security/ir.model.access.csv',
        'data/it_resource_access_data.xml',
        'data/ir_sequence.xml',
        'data/it_resource_term_data.xml',
        'views/it_resource_need_views.xml',
        'views/it_resource_item_views.xml',
        'views/it_resource_unit_views.xml',
        'views/it_resource_assignment_views.xml',
        'views/it_resource_setting_views.xml',
        'views/it_resource_access_views.xml',
        'views/it_resource_term_views.xml',
        'wizard/it_resource_approval_decide_views.xml',
        'wizard/it_resource_approval_template_views.xml',
        'views/it_resource_request_views.xml',
        'views/menus.xml',
        'views/assets.xml',
    ],
    'qweb': [
        'static/src/xml/signature.xml',
    ],
    'installable': True,
    'application': True,
}
