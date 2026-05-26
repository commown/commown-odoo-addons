# Copyright 2026 Commown SCIC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)

{
    "name": "Commown - Website designs",
    "summary": "Module to contain custom website view overrides, to better maintain them",
    "version": "16.0.1.0.1",
    "development_status": "Alpha",
    "category": "Uncategorized",
    "website": "https://github.com/commown/commown-odoo-addons",
    "author": "Commown SCIC",
    "maintainers": ["fcayre", "Honeyxilia"],
    "license": "AGPL-3",
    "depends": [
        "website_b2b",
        "website_sale",
    ],
    "data": [
        "data/website_rewrite.xml",
        "views/website_templates.xml",
    ],
}
