{
    'name': 'Commown SCIC SAS',
    'category': 'Business',
    'summary': 'Commown SCIC SAS business application',
    'version': '10.0.1.7.2',
    'description': "Commown SCIC SAS business application",
    'author': "Commown SCIC SAS",
    'license': "AGPL-3",
    'website': "https://commown.fr",
    'depends': [
        # Commown modules
        'account_bank_statement_import_credit_coop',
        'account_bank_statement_import_lanef',
        'account_move_slimpay_import',
        'commown_shipping',
        'payment_slimpay',
        'product_rental',
        'scic',
        'website_sale_affiliate_portal',
        'website_sale_b2b',
        'website_sale_coupon',

        # OCA modules
        'account_usability',  # needed for account_invoice.has_discount (py3o)
        'account_payment_sale',
        'account_mass_reconcile',
        'account_move_stripe_import',
        'auth_signup',
        'base_action_rule',
        'base_company_extension',  # required for legal_type (py3o)
        'crm',
        'l10n_fr',
        'mass_mailing',
        'mass_mailing_partner',
        'project_issue',
        'report_py3o',
        'sale_usability',  # required for sale.layout_category (py3o)
        'website_sale_cart_selectable',
        'website_sale_default_country',
        'website_sale_hide_price',
        'website_sale_require_login',
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
        'views/actions_sale_order.xml',
        'views/actions_account_invoice.xml',
        'views/product_template.xml',
        'views/project_issue.xml',
        'views/webclient_templates.xml',
        'views/website_portal_templates.xml',
        'views/website_sale_templates.xml',
        'views/website_site_portal_sale_templates.xml',
        'views/res_partner.xml',
        'views/crm_lead.xml',
        'views/crm_team.xml',
        'data/mail_templates.xml',
        'data/account_invoice_report.xml',
    ],
    'qweb': [
        'static/src/xml/account_reconciliation.xml',
    ],
    'installable': True,
    'application': True,
}
