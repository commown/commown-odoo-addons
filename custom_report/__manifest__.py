# Copyright 2022-today Commown SCIC (https://commown.coop)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Custom reports",
    "category": "Custom",
    "summary": "Custom reports",
    "version": "12.0.1.0.0",
    "description": "This module adds custom reports.",
    "author": "Commown SCIC",
    "license": "AGPL-3",
    "website": "https://commown.coop",
    "depends": [
        "account_usability",  # needed for account_invoice.has_discount (py3o)
        "base_company_extension",  # required for legal_type (py3o)
        "l10n_fr",  # required for siret (py3o)
        "product_rental",
        "report_py3o",
        "sale_usability",  # required for sale.layout_category (py3o)
        "scic",  # required for is_equity (py3o)
    ],
    "external_dependencies": {
        "python": ["py3o.template", "py3o.formats"],
    },
    "data": [
        "report/report.xml",
    ],
    "installable": True,
    "application": True,
}
