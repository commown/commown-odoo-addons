# Copyright 2026 Commown SCIC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)

{
    "name": "Project - Automatic stage changes",
    "summary": "Allow for automatic task stage changes upon receiving a message, or after a period of time",
    "version": "16.0.1.0.1",
    "development_status": "Alpha",
    "category": "Uncategorized",
    "website": "https://github.com/commown/commown-odoo-addons",
    "author": "Commown SCIC",
    "maintainers": ["fcayre", "Honeyxilia"],
    "license": "AGPL-3",
    "depends": [
        "base_automation",
        "project",
    ],
    "data": [
        "data/actions_server.xml",
        "data/base_automation.xml",
        "views/project_views.xml",
    ],
}
