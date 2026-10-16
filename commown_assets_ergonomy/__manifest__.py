# Copyright 2026 Commown SCIC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)

{
    "name": "Assets ergonomy features for Commown",
    "summary": "Adding several helpers and QOL features surrounding assets",
    "version": "16.0.1.0.0",
    "development_status": "Alpha",
    "category": "Accounting & Finance",
    "website": "https://github.com/commown/commown-odoo-addons",
    "author": "Commown SCIC",
    "maintainers": ["fcayre", "Honeyxilia"],
    "license": "AGPL-3",
    "depends": ["account_asset_management"],
    "data": [
        "data/account_journal.xml",
        "data/account.xml",
        "security/ir.model.access.csv",
        "wizards/account_asset_mass_remove.xml",
    ],
}
