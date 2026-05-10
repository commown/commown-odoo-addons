# Copyright (C) 2021 - Commown SCIC (https://commown.coop)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Account invoice merge auto pay",
    "category": "accounting",
    "version": "16.0.1.0.6",
    "author": "Commown SCIC",
    "license": "AGPL-3",
    "website": "https://github.com/commown/commown-odoo-addons",
    "depends": [
        "account_invoice_merge_payment",
        "account_invoice_merge_auto",
        "contract_payment_auto",
        "queue_job",
    ],
    "data": [
        "data/queue_job_channel.xml",
        "data/queue_job_function.xml",
    ],
    "installable": True,
}
