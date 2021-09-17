# coding: utf-8
# Copyright (C) 2018 - Today: Commown (https://commown.coop)
# @author: Florent Cayré
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Commown - LineageOS',
    'category': '',
    'version': '10.0.0.0.1',
    'author': "Commown SCIC SAS",
    'license': "AGPL-3",
    'website': "https://commown.coop",
    'external_dependencies': {
        # 'python': []
    },
    'depends': [
        'base_action_rule',
        'crm',
        'commown_shipping',
    ],
    'data': [
        'data/actions.xml',
    ],
    'installable': True,
    'application': False,
}
