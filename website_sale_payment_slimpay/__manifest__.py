# Copyright 2020 Commown SCIC (https://commown.coop)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Slimpay online payment and mandate signing for e-commerce",
    "summary": "Provide website customers online SEPA mandate signing with Slimpay",
    "version": "16.0.1.0.0",
    "development_status": "Beta",
    "category": "e-commerce",
    "website": "https://github.com/commown/commown-odoo-addons",
    "author": "Commown SCIC",
    "maintainers": ["fcayre"],
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": ["website_sale", "account_payment_slimpay"],
    "data": [
        "views/address_template.xml",
        "views/payment_templates.xml",
        "data/payment_provider.xml",  # After redirect_form definition!
    ],
}
