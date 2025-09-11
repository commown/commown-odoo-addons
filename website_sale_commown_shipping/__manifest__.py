# Copyright 2025 Commown SCIC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)

{
    "name": "Commown Shipping - Website Sale integration",
    "summary": "Integrate address validation from commown_shipping into the website sale address form.",
    "version": "16.0.1.0.0",
    "development_status": "Alpha",
    "category": "Uncategorized",
    "website": "https://github.com/commown/commown-odoo-addons",
    "author": "Commown SCIC",
    "maintainers": ["fcayre", "Honeyxilia"],
    "license": "AGPL-3",
    "depends": [
        "commown_shipping",
        "website_sale",
        "website_sale_partner_firstname",
    ],
    "data": [
        "views/address_template.xml",
        "views/payment_template.xml",
    ],
}
