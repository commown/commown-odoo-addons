{
    "name": "Account invoice merge auto",
    "category": "Accounting",
    "summary": "",
    "version": "16.0.1.0.0",
    "author": "Commown SCIC",
    "license": "AGPL-3",
    "website": "https://github.com/commown/commown-odoo-addons",
    "depends": [
        "account_invoice_merge",
    ],
    "external_dependencies": {},
    "data": [
        "data/crontab.xml",
        "views/res_partner.xml",
        "views/account_invoice.xml",
    ],
    "installable": True,
}
