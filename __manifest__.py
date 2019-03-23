{
    'name': 'Rating project issue: Net Promoter Score',
    'category': 'Business',
    'summary': 'Implement net promoter score on top of odoo project issue rating',
    'version': '10.0.1.0.0',
    'author': "Commown SCIC SAS",
    'license': "AGPL-3",
    'website': "https://commown.fr",
    'depends': [
        'rating_project_issue',
    ],
    'external_dependencies': {
    },
    'data': [
        'data/mail_templates.xml',
        'data/web_templates.xml',
    ],
    'installable': True,
}
