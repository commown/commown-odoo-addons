# coding: utf-8
# Copyright (C) 2018 - Today: Commown (https://commown.fr)
# @author: Florent Cayré
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Import Crédit Coopératif bank statements',
    'category': 'Accouting',
    'version': '10.0.1.0.0',
    'author': "Commown SCIC SAS",
    'license': "AGPL-3",
    'website': "https://commown.fr",
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
