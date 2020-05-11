# coding: utf-8
# Copyright (C) 2018 - Today: Commown (https://commown.coop)
# @author: Florent Cayré
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Commown Self Troubleshooting',
    'category': '',
    'version': '10.0.0.0.2',
    'author': "Commown SCIC SAS",
    'license': "AGPL-3",
    'website': "https://commown.coop",
    'external_dependencies': {
    },
    'depends': [
        'project',
    ],
    'data': [
        'data/FP2/camera/form.xml',
        'data/FP2/camera/issue_template.xml',
        'data/FP2/micro/form.xml',
        'data/FP2/micro/issue_template.xml',
        'data/common_steps.xml',
        'data/project.xml',
        'data/tags.xml',
        'views/website_portal_templates.xml',
    ],
    'installable': True,
    'application': False,
}
