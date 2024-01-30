{
    "name": "Website sale B2B",
    "category": "Business",
    "summary": "Adapt website_sale module to mixed B2C/ B2B products",
    "version": "12.0.1.1.8",
    "description": (
        "Add a professional products category and display all"
        " products in it excl. taxes"
    ),
    "author": "Commown SCIC",
    "license": "AGPL-3",
    "website": "https://commown.coop",
    "depends": [
        "crm",
        "mail",
        "product_rental",
        "website_sale",
    ],
    "external_dependencies": {},
    "data": [
        "data/crm.xml",
        "data/ir_config_parameter.xml",
        "data/mail_template.xml",
        "data/res_partner.xml",
        "data/website.xml",
        "views/login.xml",
        "views/payment_portal_templates.xml",
        "views/portal_wizard.xml",
        "views/product_pricelist.xml",
        "views/product_template.xml",
        "views/res_users.xml",
        "views/sale_portal_templates.xml",
        "views/signup.xml",
        "views/website.xml",
        "views/website_sale_order.xml",
        "views/website_sale_product.xml",
    ],
    "installable": True,
}
