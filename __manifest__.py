{
    'name': 'Urban mine',
    'category': 'Business',
    'summary': 'Urban mine offer: people sell their device to the company',
    'version': '10.0.1.0.0',
    'description': 'Urban mine offer: people sell their device to the company',
    'author': "Commown SCIC SAS",
    'license': "AGPL-3",
    'website': "https://commown.fr",
    'depends': [
        'crm',
        'website_form_builder',
        'website_form_recaptcha',
    ],
    'external_dependencies': {
    },
    'data': [
        'data/model.xml',
        'data/crm.xml',
        'data/registration_page.xml',
        'data/actions.xml',
        'data/mail_templates.xml',
    ],
    'installable': True,
}
