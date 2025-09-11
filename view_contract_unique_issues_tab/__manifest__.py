# Copyright 2025 Commown SCIC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)

{
    "name": "View - Place all contract-related issues in a single tab",
    "summary": "Unite any given contract's contractual or payment issues in a dedicated tab.",
    "version": "16.0.1.0.1",
    "development_status": "Alpha",
    "category": "Uncategorized",
    "website": "https://github.com/commown/commown-odoo-addons",
    "author": "Commown SCIC",
    "maintainers": ["fcayre", "Honeyxilia"],
    "license": "AGPL-3",
    "depends": [
        "commown_contractual_issue",
        "contract_payment_issues",
    ],
    "data": [
        "views/contract_contract.xml",
    ],
}
