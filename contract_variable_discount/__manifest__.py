# Copyright (C) 2021 - Commown (https://commown.coop)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Contract variable discount",
    "category": "Contract Management",
    "version": "12.0.1.2.8",
    "author": "Commown SCIC",
    "license": "AGPL-3",
    "website": "https://commown.coop",
    "depends": [
        "product_rental",  # for contract.line's contract_template_line_id field
        "web_domain_field",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/contract.xml",
        "views/contract_template.xml",
        "views/discount.xml",
    ],
    "installable": True,
}
