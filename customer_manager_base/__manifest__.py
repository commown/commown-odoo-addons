# Copyright 2024 Commown <contact@commown.coop>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Customer manager base",
    "summary": "Base module to allow customers to manage things efficiently",
    "version": "12.0.1.0.1",
    "development_status": "Alpha",
    "category": "Manager customer",
    "website": "https://commown.coop",
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
        "views/customer_group_wizard.xml",
        "views/project.xml",
    ],
    "installable": True,
}
