{
    'name': 'Commown lead risk analysis',
    'category': 'Business',
    'summary': 'Add risk analysis-related fields to leads',
    'version': '12.0.1.0.0',
    'description': 'Risk analysis data storage for Commown leads',
    'author': "Commown SCIC SAS",
    'license': "AGPL-3",
    'website': "https://github.com/commown/commown-odoo-addons",
    'depends': [
        'crm',
    ],
    'data': [
        'views/crm_team.xml',
        'views/crm_lead.xml',
    ],
    'installable': True,
}
