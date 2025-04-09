{
    "name": "Website sale coupon",
    "category": "Business",
    "summary": (
        "Manage promotion campaigns with or without coupons."
        " Coupons are secret codes that customers can get (paid or for free)"
        " to get an advantage when they buy a product on the online shop."
    ),
    "version": "12.0.1.1.1",
    "author": "Commown SCIC",
    "license": "AGPL-3",
    "website": "https://github.com/commown/commown-odoo-addons",
    "depends": [
        "website_sale",
    ],
    "external_dependencies": {},
    "data": [
        "security/ir.model.access.csv",
        "views/backoffice.xml",
        "views/website.xml",
        "views/wizard_create_multiple_coupons.xml",
    ],
    "installable": True,
}
