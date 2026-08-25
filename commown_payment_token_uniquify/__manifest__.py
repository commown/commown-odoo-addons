# Copyright 2025 Commown SCIC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)

{
    "name": "Commown payment token uniquify customization",
    "summary": "Add more payment_token_uniquify obsolescence actions to automatically reattribute invoices and contracts.",
    "version": "16.0.1.0.3",
    "development_status": "Alpha",
    "category": "Accounting/Payment",
    "website": "https://github.com/commown/commown-odoo-addons",
    "author": "Commown SCIC",
    "maintainers": ["fcayre", "Honeyxilia"],
    "license": "AGPL-3",
    "depends": [
        "account_payment_partner",
        "contract_auto_merge_invoice",
        "payment_token_uniquify",
    ],
    "data": [
        "data/obsolescence_action.xml",
    ],
}
