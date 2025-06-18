# Copyright (C) 2021 - Commown SCIC (https://commown.coop)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Contract variable discount for Commown",
    "category": "Contract Management",
    "version": "16.0.1.0.4",
    "author": "Commown SCIC",
    "license": "AGPL-3",
    "website": "https://github.com/commown/commown-odoo-addons",
    "depends": [
        "commown_contractual_issue",
        "contract_variable_discount",
        "product_rental",
        "website_sale_coupon",
    ],
    "installable": True,
    "data": [
        "views/discount.xml",
    ],
}
