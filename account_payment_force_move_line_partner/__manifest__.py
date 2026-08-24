# Copyright 2026 Commown SCIC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)

{
    "name": "Account payment - Force move line partner",
    "summary": "Wizard to force a different partner on an account move line related to an account payment",
    "version": "16.0.1.0.1",
    "development_status": "Alpha",
    "category": "Uncategorized",
    "website": "https://github.com/commown/commown-odoo-addons",
    "author": "Commown SCIC",
    "maintainers": ["fcayre", "Honeyxilia"],
    "license": "AGPL-3",
    "depends": [
        "account",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizards/wiz_force_move_line_partner.xml",
    ],
}
