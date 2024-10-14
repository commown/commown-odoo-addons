# Copyright 2024 Commown <contact@commown.coop>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Customer team manager",
    "summary": "Allow customers to manage their team and users",
    "version": "12.0.1.0.0",
    "development_status": "Alpha",
    "category": "Manager customer",
    "website": "https://commown.coop",
    "author": "Commown SCIC",
    "maintainers": ["fcayre"],
    "license": "AGPL-3",
    "depends": [
        # native modules
        "account",
        "portal",
        "sale",
        # OCA modules
        "partner_firstname",
        "web_notify",
        # Commown modules
        "server_actions_auth",
        "customer_manager_base",
    ],
    "data": [
        "security/groups.xml",
        "security/ir.model.access.csv",
        "security/rules.xml",
        "data/action_res_partner.xml",
        "data/roles.xml",
        "views/wizard_portal_access.xml",  # referenced in customer_team_manager.xml!
        "views/customer_team_manager.xml",
        "views/portal_templates.xml",
    ],
    "installable": True,
}
