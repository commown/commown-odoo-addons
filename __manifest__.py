{
    'name': 'Commown lead risk analysis',
    'category': 'Business',
    'summary': 'Add risk analysis-related fields to leads',
    'version': '10.0.0.0.3',
    'description': 'Risk analysis data storage for Commown leads',
    'author': "Commown SCIC SAS",
    'license': "AGPL-3",
    'website': "https://commown.fr",
    'depends': [
        'crm',
        'partner_firstname',
        'product_rental',
    ],
    'data': [
        'views/crm_team.xml',
        'views/crm_lead.xml',
    ],
    'installable': True,
}
