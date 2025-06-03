# Copyright (C) 2018 - Today: Commown SCIC (https://commown.coop)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Payment Slimpay issue",
    "category": "Website",
    "version": "16.0.1.0.1",
    "author": "Commown SCIC",
    "license": "AGPL-3",
    "website": "https://github.com/commown/commown-odoo-addons",
    "depends": [
        "account_payment_partner",
        "account_payment_slimpay",
        "base_automation",
        "contract_payment_auto",
        "commown_res_partner_sms",
        "project",
        "queue_job",
    ],
    "data": [
        "data/mail_template.xml",
        "data/project.xml",
        "data/product.xml",
        "data/cron.xml",
        "data/action.xml",
        "data/res_partner.xml",
        "views/project_task.xml",
    ],
    "installable": True,
}
