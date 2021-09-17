# coding: utf-8
# Copyright (C) 2019 - Today: Commown (https://commown.coop)
# @author: Florent Cayré
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Contract auto merge invoice',
    'category': 'Accounting',
    'version': '10.0.0.0.1',
    'author': "Commown SCIC SAS",
    'license': "AGPL-3",
    'website': "https://commown.coop",

    'depends': [
        'contract',
        'account_invoice_merge_auto',
    ],

    'installable': True,
    'application': False,
}
