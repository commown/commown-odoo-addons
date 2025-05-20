# Copyright 2024 Commown <contact@commown.coop>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Customer team manager",
    "summary": "Allow customers to manage their team and users",
    "version": "16.0.1.0.0",
    "development_status": "Alpha",
    "category": "Manager customer",
    "website": "https://github.com/commown/commown-odoo-addons",
    "author": "Commown SCIC",
    "maintainers": ["fcayre"],
    "license": "AGPL-3",
    "depends": [
        # native modules
        "account",
        "portal",
        "sale",
        # OCA modules
        "base_fontawesome",
        "partner_firstname",
        "web_notify",
        # Commown modules
        "server_actions_auth",
        "customer_manager_base",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/rules.xml",
        "data/customer_roles.xml",
        "views/wizard_portal_access.xml",  # referenced in customer_team_manager.xml!
        "views/customer_team_manager.xml",
        "views/portal_templates.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "/customer_team_manager/static/src/xml/field_widget_template.xml",
            "/customer_team_manager/static/src/xml/export_data_dialog.xml",
            "/customer_team_manager/static/src/css/export.css",
            "/customer_team_manager/static/src/scss/field_widget.scss",
            "/customer_team_manager/static/src/js/field_widget.esm.js",
            "/customer_team_manager/static/src/js/export_data_dialog.esm.js",
        ],
    },
    "installable": True,
}
