# Copyright 2024 Commown <contact@commown.coop>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Server actions authorization",
    "summary": "Add groups_id on ir.actions.server to restrict their usage to groups",
    "version": "12.0.1.0.1",
    "development_status": "Alpha",
    "category": "Tools",
    "website": "https://commown.coop",
    "author": "Commown SCIC",
    "maintainers": ["fcayre"],
    "license": "AGPL-3",
    "installable": True,
    "data": [
        "views/ir_actions_server.xml",
    ],
}
