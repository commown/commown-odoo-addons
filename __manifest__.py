# coding: utf-8
# Copyright (C) 2021: Commown (https://commown.coop)
# @author: Florent Cayré
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Commown devices',
    'category': 'stock',
    'version': '10.0.1.0.0',
    'author': "Commown SCIC",
    'license': "AGPL-3",
    'website': "https://commown.coop",
    'depends': [
        'commown_shipping',
        'product_rental',
        'stock',
    ],
    'data': [
        'data/action_crm_lead.xml',
        'data/stock_location.xml',
        'views/contract.xml',
        'views/product.xml',
    ],
    'installable': True,
}
