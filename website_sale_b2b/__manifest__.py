{
    "name": "Website sale B2B",
    "category": "Business",
    "summary": "Adapt website_sale module to mixed B2C/ B2B products",
    "version": "12.0.1.0.0",
    "description": (
        "Add a professional products category and display all"
        " products in it excl. taxes"
    ),
    "author": "Commown SCIC",
    "license": "AGPL-3",
    "website": "https://commown.coop",
    "depends": [
        "product_rental",
        "website_sale",
    ],
    "external_dependencies": {},
    "data": [
        "data/product_public_category.xml",
        "views/website_sale_product.xml",
        "views/product_template.xml",
    ],
    "installable": True,
}
