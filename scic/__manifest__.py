# Copyright 2020 Commown SCIC SAS (https://commown.fr)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': "SCIC (Société Coopérative d'Intérêts Collectifs)",
    'category': 'Custom',
    'summary': 'Module that defines functionalities related to the SCIC companies',
    'version': '12.0.1.0.0',
    'description': """
    SCIC
    ====
    This module adds functionalities:

- ability to mark products as equities
    """,
    'author': "Commown SCIC SAS",
    'license': "AGPL-3",
    'website': "https://github.com/commown/commown-odoo-addons",
    'depends': [
        'website_sale',
    ],
    'data': [
        'views/product_template.xml',
    ],
    'installable': True,
    'application': True,
}
