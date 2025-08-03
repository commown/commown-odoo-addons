# Copyright 2025 Commown SCIC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)

{
    "name": "Portal - Add firstname/lastname fields edition",
    "summary": "Replace the name field by firstname/lastname from partner_firstname in the portal templates.",
    "version": "16.0.1.0.1",
    "development_status": "Alpha",
    "category": "Uncategorized",
    "website": "https://github.com/commown/commown-odoo-addons",
    "author": "Commown SCIC",
    "maintainers": ["fcayre", "Honeyxilia"],
    "license": "AGPL-3",
    "depends": [
        "partner_firstname",
        "portal",
    ],
    "data": [
        "views/auth_signup.xml",
        "views/website_portal_templates.xml",
    ],
}
