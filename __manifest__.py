{
    'name': 'Commown shipping',
    'category': 'Business',
    'summary': 'Commown shipping-related features',
    'version': '10.0.1.0.0',
    'description': 'Commown label printing and shipping followup',
    'author': "Commown SCIC SAS",
    'license': "AGPL-3",
    'website': "https://commown.fr",
    'depends': [
        'crm',
        'keychain',
        'partner_firstname',
    ],
    'external_dependencies': {
        'bin': ['pdfjam'],
    },
    'data': [
        'security/ir.model.access.csv',
    ],
    'installable': True,
}
