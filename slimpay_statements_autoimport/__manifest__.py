# Copyright 2023 Commown SCIC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)

{
    "name": "Slimpay statements automatic import",
    "summary": "Regularly fetch Slimpay statements and import them",
    "version": "12.0.1.0.3",
    "development_status": "Alpha",
    "category": "Accounting/Accounting",
    "website": "https://github.com/commown/commown-odoo-addons",
    "author": "Commown SCIC",
    "maintainers": ["fcayre"],
    "license": "AGPL-3",
    "installable": True,
    "depends": [
        "account_move_slimpay_import",
        "account_payment_slimpay",
        "fetchmail",
        "queue_job",
    ],
    "data": [
        "data/cron.xml",
        "data/ir_config_parameter.xml",
        "data/mail_alias.xml",
        "security/ir.model.access.csv",
        "views/statement_import.xml",
    ],
}
