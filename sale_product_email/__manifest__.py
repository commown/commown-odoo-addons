{
    'name': 'Sale product email',
    'category': 'e-commerce',
    'summary': "Send a product-specific email to its buyers",
    'version': '10.0.0.0.1',
    'author': "Commown SCIC SAS",
    'license': "AGPL-3",
    'website': "https://commown.fr",
    'data': [
        'data/sale_order_actions.xml',
        'views/product_template.xml',
    ],
    'depends': [
        'website_sale',
    ],
    'installable': True,
}
