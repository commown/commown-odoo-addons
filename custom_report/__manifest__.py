# Copyright 2020 Commown SCIC SAS (https://commown.fr)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': 'Custom reports',
    'category': 'Custom',
    'summary': 'Custom reports',
    'version': '12.0.1.0.0',
    'description': """
    Custom Reports
    ==============
    This module adds custom reports.
    """,
    'author': "Commown SCIC SAS",
    'license': "AGPL-3",
    'website': "https://commown.fr",
    'depends': [
        'report_py3o',
        'account_usability',  # needed for account_invoice.has_discount (py3o)
        'base_company_extension',  # required for legal_type (py3o)
        'sale_usability',  # required for sale.layout_category (py3o)
        'l10n_fr',   # required for siret (py3o)
        'scic',     # required for is_equity (py3o)
    ],
    'data': [
        'report/report.xml',
    ],
    'installable': True,
    'application': True,
}
