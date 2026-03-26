# Copyright 2022-today Commown SCIC (https://commown.coop)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Custom reports",
    "category": "Custom",
    "summary": "Custom reports",
    "version": "16.0.1.0.6",
    "author": "Commown SCIC",
    "license": "AGPL-3",
    "website": "https://github.com/commown/commown-odoo-addons",
    "depends": [
        "base_company_extension",  # required for legal_type (py3o)
        "l10n_fr",  # required for siret (py3o)
        "product_rental",
        "report_py3o",
        "sale_usability",  # required for py3o_lines_layout + invoice.has_discount
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
