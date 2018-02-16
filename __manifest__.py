{
    'name': 'Commown SCIC SAS',
    'category': 'Business',
    'summary': 'Commown SCIC SAS business application',
    'version': '10.0.1.0.0',
    'description': """Commown SCIC SAS business application on top of dependant modules""",
    'author': "Commown SCIC SAS",
    'license': "AGPL-3",
    'website': "https://commown.fr",
    'depends': [
        'payment_slimpay', 'l10n_fr_certification', 'base_action_rule',
        'website_sale_default_country', 'auth_signup',
        'website_sale_require_login', 'product_rental', 'scic',
        'crm', 'mass_mailing', 'project_issue', 'website_sale_hide_price',
        'mass_mailing_partner',
    ],
    'external_dependencies': {
        'python': ['magic']
    },
    'data': [
        'views/address_template.xml',
        'views/auth_signup.xml',
        'views/cart.xml',
        'views/favicon.xml',
        'views/sale_order.xml',
        'views/product_template.xml',
        'views/website_portal_templates.xml',
        'views/res_partner.xml',
    ],
    'installable': True,
    'application': True,
}
