# Copyright (C) 2021 Commown SCIC (https://commown.coop)
# @author: Florent Cayré
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Payment Slimpay dump and restore utils',
    'category': 'Website',
    'version': '12.0.1.0.0',
    'author': "Commown SCIC",
    'license': "AGPL-3",
    'website': "https://commown.coop",
    'depends': [
        'account_payment_slimpay',
    ],
    'data': [
        'data/cron.xml',
    ],
    'installable': True,
}
