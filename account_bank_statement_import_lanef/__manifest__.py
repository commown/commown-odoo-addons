# coding: utf-8
# Copyright (C) 2021 - Today: Commown (https://commown.coop)
# @author: Florent Cayré
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Import La Nef CSV bank statements',
    'category': 'Accouting',
    'version': '10.0.2.0.0',
    'author': "Commown SCIC",
    'license': "AGPL-3",
    'website': "https://commown.coop",
    'depends': [
        'account_bank_statement_import',
    ],
    'external_dependencies': {
        'python': ['unicodecsv'],
    },
    'data': [
        'views/account_bank_statement_import.xml',
    ],
    'installable': True,
}
