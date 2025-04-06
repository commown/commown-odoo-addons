# Copyright 2018 Commown (https://commown.coop).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Account Move Slimpay Import",
    "summary": "Import Slimpay payment reports",
    "version": "12.0.1.1.2",
    "category": "Finance",
    "website": "https://github.com/commown/commown-odoo-addons",
    "author": "Commown SCIC",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "external_dependencies": {
        "python": [],
        "bin": [],
    },
    "depends": [
        "account_move_base_import",
        "l10n_fr",
    ],
    "data": [
        "data/partner.xml",
        "data/account_account.xml",
        "data/account_journal.xml",
    ],
    "demo": [],
    "qweb": [],
}
