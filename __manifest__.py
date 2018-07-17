{
    'name': 'Website sale coupon',
    'category': 'Business',
    'summary': ('Emit coupons that customers can buy elsewhere'
                ' and use to reduce the price of a product on your shop'),
    'version': '10.0.1.0.0',
    'description': ('Emit coupons that customers can buy elsewhere'
                    ' and use to reduce the price of a product on your shop'),
    'author': "Commown SCIC SAS",
    'license': "AGPL-3",
    'website': "https://commown.fr",
    'depends': [
        'website_sale',
    ],
    'external_dependencies': {
    },
    'data': [
        'security/ir.model.access.csv',
        'views/backoffice.xml',
        'views/website.xml',
    ],
    'installable': True,
}
