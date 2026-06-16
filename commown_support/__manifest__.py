# Copyright 2025 Commown SCIC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)

{
    "name": "Commown Support",
    "summary": "Features related to Commown's tech support",
    "version": "16.0.1.0.7",
    "development_status": "Beta",
    "category": "Uncategorized",
    "website": "https://github.com/commown/commown-odoo-addons",
    "author": "Commown SCIC",
    "maintainers": ["fcayre", "Honeyxilia"],
    "license": "AGPL-3",
    "depends": [
        # Odoo modules
        "base_automation",
        # OCA modules
        "partner_firstname",
        "queue_job",
        # Commown modules
        "commown_contractual_issue",
        "commown_project",
        "commown_res_partner_sms",
    ],
    "data": [
        "data/mail_templates.xml",
        "data/ir_actions_server.xml",
        "data/base_automation.xml",
        "data/project.xml",
        "views/project_project.xml",
        "views/project_task.xml",
    ],
}
