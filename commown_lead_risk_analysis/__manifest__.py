{
    "name": "Commown lead risk analysis",
    "category": "Business",
    "summary": "Add risk analysis-related fields to leads",
    "version": "16.0.1.0.0",
    "author": "Commown SCIC",
    "license": "AGPL-3",
    "website": "https://github.com/commown/commown-odoo-addons",
    "depends": [
        "crm",
        "partner_firstname",
        "product_rental",
        "commown_contractual_issue",
    ],
    "data": [
        "data/project_task_template.xml",
        "views/crm_lead.xml",
        "views/crm_team.xml",
        "views/product_template.xml",
    ],
    "installable": True,
}
