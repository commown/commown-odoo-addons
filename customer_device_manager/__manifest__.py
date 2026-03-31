# Copyright 2025 Commown <contact@commown.coop>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Customer device manager",
    "summary": "Allow customers to assign devices to users",
    "version": "16.0.1.0.5",
    "development_status": "Alpha",
    "category": "Manager customer",
    "website": "https://github.com/commown/commown-odoo-addons",
    "author": "Commown SCIC",
    "maintainers": ["Honeyxilia", "fcayre"],
    "license": "AGPL-3",
    "depends": [
        # Commown modules
        "commown_devices",
        "customer_team_manager",
        "date_range_portal",
    ],
    "data": [
        "security/groups.xml",
        "data/customer_roles.xml",
        "security/ir.model.access.csv",
        "security/rules.xml",
        "data/actions_act_url.xml",
        "data/ir_ui_menu.xml",
        "views/device_assignment.xml",
        "views/portal_templates.xml",
    ],
    "installable": True,
}
