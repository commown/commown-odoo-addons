{
    'name': "SCIC (Société Coopérative d'Intérêts Collectifs)",
    'category': 'Business',
    'summary': 'Module that defines functionalities related to the SCIC companies',
    'version': '10.0.1.0.0',
    'description': """
Added functionalities:

- ability to mark products as equities, so that they can be sold online
""",
    'author': "Commown SCIC SAS",
    'license': "AGPL-3",
    'website': "https://commown.fr",
    'depends': ['website_sale'],
    'external_dependencies': {},
    'data': [
        'views/product_template.xml',
    ],
    'installable': True,
}
