# coding: utf-8
# Copyright (C) 2018 - Today: Commown (https://commown.coop)
# @author: Florent Cayré
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Commown contractual issues management',
    'category': '',
    'version': '10.0.0.0.1',
    'author': "Commown SCIC SAS",
    'license': "AGPL-3",
    'website': "https://commown.coop",
    'depends': [
        'project_issue',
        'contract',
    ],
    'data': [
        'views/project.xml',
        'views/project_issue.xml',
        'views/project_task.xml'
    ],
    'installable': True,
    'application': False,
}
