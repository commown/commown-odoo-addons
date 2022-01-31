# Copyright (C) 2021: Commown (https://commown.coop)
# @author: Florent Cayré
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Contract auto merge invoice',
    'category': 'Accounting',
    'version': '12.0.1.0.0',
    'author': "Commown SCIC SAS",
    'license': "AGPL-3",
    'website': "https://github.com/commown/commown-odoo-addons",

    'depends': [
        'contract',
        'account_invoice_merge_auto',
    ],

    'installable': True,
    'application': False,
}
