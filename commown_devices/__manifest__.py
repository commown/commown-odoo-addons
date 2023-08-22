# Copyright (C) 2021: Commown (https://commown.coop)
# @author: Florent Cayré
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Commown devices",
    "category": "stock",
    "version": "12.0.1.1.2",
    "author": "Commown SCIC",
    "license": "AGPL-3",
    "website": "https://commown.coop",
    "depends": [
        "commown_contractual_issue",
        "commown_shipping",
        "commown_lead_risk_analysis",
        "product_rental",
        "stock",
    ],
    "data": [
        "data/action_crm_lead.xml",
        "data/action_picking.xml",
        "data/action_project_task.xml",
        "data/project_task.xml",
        "data/stock_location.xml",
        "security/ir.model.access.csv",
        "views/contract.xml",
        "views/product.xml",
        "views/project_project.xml",
        "views/project_task.xml",
        "views/project_task_type.xml",
        "views/stock_picking.xml",
        "views/wizard_crm_lead_picking.xml",
        "views/wizard_project_task_picking.xml",
    ],
    "demo": [
        "demo/project_task.xml",
    ],
    "installable": True,
}
