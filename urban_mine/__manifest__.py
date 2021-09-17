# Copyright 2020 Commown SCIC SAS (https://commown.fr)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': 'Urban mine',
    'category': 'Custom',
    'summary': 'Urban mine offer: people sell their device to the company',
    'version': '12.0.1.0.0',
    'description': 'Urban mine offer: people sell their device to the company',
    'author': 'Commown SCIC SAS',
    'license': 'AGPL-3',
    'website': 'https://commown.fr',
    'depends': [
        'commown_shipping',
        'l10n_fr',
        'crm',
        'website_sale_promotion_rule',
        'website_form_builder',
        'website_form_recaptcha',
        'report_py3o',
    ],
    'data': [
        'data/model.xml',
        'data/product.xml',
        'data/crm.xml',
        'data/report.xml',
        'data/registration_page.xml',
        'data/actions.xml',
        'data/mail_templates.xml',
        'data/coupon.xml',
    ],
    'installable': True,
}
