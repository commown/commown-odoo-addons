# Copyright 2025 Commown SCIC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)

{
    "name": "Partner action - Set invoice recipent",
    "summary": "Adds an action to set a given user as an invoice recipent, if their parent partner has a payment token",
    "version": "16.0.1.0.3",
    "development_status": "Beta",
    "category": "Uncategorized",
    "website": "https://github.com/commown/commown-odoo-addons",
    "author": "Commown SCIC",
    "maintainers": ["fcayre", "Honeyxilia"],
    "license": "AGPL-3",
    "depends": [
        # Odoo modules
        "web_notify",
        # OCA module
        "base_fontawesome",
        "contract_payment_auto",
    ],
    "data": [
        "views/res_partner.xml",
    ],
}
