# Copyright 2025 Commown SCIC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)

{
    "name": "Website B2B",
    "summary": "Create a separate website for B2B users",
    "version": "16.0.1.0.0",
    "development_status": "Beta",
    "category": "Uncategorized",
    "website": "https://github.com/commown/commown-odoo-addons",
    "author": "Commown SCIC",
    "maintainers": ["fcayre", "Honeyxilia"],
    "license": "AGPL-3",
    "depends": [
        "portal",
        "website",
    ],
    "data": [
        "data/website.xml",
        "views/login.xml",
        "views/portal_wizard.xml",
        "views/res_users.xml",
        "views/signup.xml",
        "views/website.xml",
    ],
}
