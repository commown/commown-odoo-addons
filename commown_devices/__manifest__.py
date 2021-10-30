# coding: utf-8
# Copyright (C) 2021: Commown (https://commown.coop)
# @author: Florent Cayré
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Commown devices',
    'category': 'stock',
    'version': '10.0.1.3.1',
    'author': "Commown SCIC",
    'license': "AGPL-3",
    'website': "https://commown.coop",
    'depends': [
        'commown_contractual_issue',
        'commown_shipping',
        'product_rental',
        'stock',
    ],
    'data': [
        'data/action_crm_lead.xml',
        'data/action_project_issue.xml',
        'data/action_project_task.xml',
        'data/stock_location.xml',
        'views/contract.xml',
        'views/product.xml',
        'views/project_issue.xml',
        'views/project_project.xml',
        'views/project_task.xml',
        'views/wizard_crm_lead_picking.xml',
        'views/wizard_project_issue_picking.xml',
        'views/wizard_project_task_picking.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
}
