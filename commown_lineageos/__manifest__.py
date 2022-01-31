# Copyright (C) 2021 Commown SCIC (https://commown.coop)
# @author: Florent Cayré
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Commown - LineageOS',
    'category': '',
    'version': '12.0.1.0.0',
    'author': "Commown SCIC",
    'license': "AGPL-3",
    'website': "https://github.com/commown/commown-odoo-addons",
    'external_dependencies': {
        # 'python': []
    },
    'depends': [
        'base_automation',
        'crm',
        'commown_shipping',
    ],
    'data': [
        'data/actions.xml',
    ],
    'installable': True,
    'application': False,
}
