# Copyright 2024 Commown <contact@commown.coop>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Customer manager base",
    "summary": "Base module to allow customers to manage things efficiently",
    "version": "16.0.1.0.0",
    "development_status": "Alpha",
    "category": "Manager customer",
    "website": "https://github.com/commown/commown-odoo-addons",
    "author": "Commown SCIC",
    "maintainers": ["fcayre"],
    "license": "AGPL-3",
    "depends": [
        "account",
        "portal",
        "project",
        "sale",
    ],
    "data": [
        "security/groups.xml",
        "security/rules.xml",
        "views/project.xml",
    ],
    "installable": True,
}
