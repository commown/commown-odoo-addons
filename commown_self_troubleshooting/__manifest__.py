# Copyright (C) 2021 Commown SCIC (https://commown.coop)
# @author: Florent Cayré
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Commown Self Troubleshooting',
    'category': '',
    'version': '12.0.1.0.0',
    'author': "Commown SCIC",
    'license': "AGPL-3",
    'website': "https://github.com/commown/commown-odoo-addons",
    'external_dependencies': {
    },
    'depends': [
        'project',
        'commown_shipping',
    ],
    'data': [
        'data/FP2/camera/form.xml',
        'data/FP2/camera/issue_template.xml',
        'data/FP2/micro/form.xml',
        'data/FP2/micro/issue_template.xml',
        'data/FP2/battery/form.xml',
        'data/FP2/battery/issue_template.xml',
        'data/FP3/screen_protection/form.xml',
        'data/FP3/screen_protection/issue_template.xml',
        'data/GS/form_day.xml',
        'data/GS/issue_template.xml',
        'data/common_steps.xml',
        'data/project.xml',
        'data/tags.xml',
        'views/website_portal_templates.xml',
    ],
    'installable': True,
    'application': False,
}
