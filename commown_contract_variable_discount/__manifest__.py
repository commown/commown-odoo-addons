# Copyright (C) 2021 - Commown (https://commown.coop)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Contract variable discount for Commown',
    'description': ('This modules implements variable discount'
                    ' features that are specific to Commown'),
    'category': 'Contract Management',
    'version': '12.0.1.0.0',
    'author': "Commown SCIC",
    'license': "AGPL-3",
    'website': "https://github.com/commown/commown-odoo-addons",
    'depends': [
        'commown_contractual_issue',
        'contract_variable_discount',
        'product_rental',
        'website_sale_coupon',
    ],
    'installable': True,
    'data': [
        'views/discount.xml',
    ],
}
