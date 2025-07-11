# Copyright (C) 2021 Commown SCIC (https://commown.coop)
# @author: Florent Cayré
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Payment Slimpay dump and restore utils",
    "category": "Website",
    "version": "16.0.1.0.1",
    "author": "Commown SCIC",
    "license": "AGPL-3",
    "website": "https://github.com/commown/commown-odoo-addons",
    "depends": [
        "account_payment_slimpay",
        "contract_payment_auto",
    ],
    "data": [
        "data/cron.xml",
    ],
    "installable": True,
}
