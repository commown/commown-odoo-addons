{
    'name': 'Commown SCIC SAS',
    'category': 'Business',
    'summary': 'Commown SCIC SAS business application',
    'version': '10.0.1.3.2',
    'description': """Commown SCIC SAS business application on top of dependant modules""",
    'author': "Commown SCIC SAS",
    'license': "AGPL-3",
    'website': "https://commown.fr",
    'depends': [
        'payment_slimpay', 'l10n_fr', 'base_action_rule',
        'website_sale_default_country', 'auth_signup',
        'website_sale_require_login', 'product_rental', 'scic',
        'crm', 'mass_mailing', 'project_issue', 'website_sale_hide_price',
        'mass_mailing_partner', 'report_py3o',
        # odt template dependencies:
        'base_company_extension',  # required for legal_type
        'sale_usability',  # required for sale.layout_category
        'account_usability',  # required for account_invoice.has_discount
        'account_payment_sale',
        'website_sale_coupon',
        'website_sale_affiliate_portal',
        'account_mass_reconcile', 'account_move_stripe_import',
    ],
    'external_dependencies': {
        'python': ['magic'],
        'bin': ['rsvg-convert'],
    },
    'data': [
        'views/account_analytic_account.xml',
        'views/account_analytic_contract.xml',
        'views/address_template.xml',
        'views/auth_signup.xml',
        'views/cart.xml',
        'views/favicon.xml',
        'views/sale_order.xml',
        'views/product_template.xml',
        'views/website_portal_templates.xml',
        'views/website_sale_templates.xml',
        'views/website_site_portal_sale_templates.xml',
        'views/res_partner.xml',
        'views/crm_lead.xml',
        'views/crm_team.xml',
        'data/mail_templates.xml',
        'data/account_invoice_report.xml',
    ],
    'installable': True,
    'application': True,
}
