# Copyright (C) 2022-today: Commown (https://commown.coop)
# @author: Luc Parent
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


{
    "name": "Commown Shareholder Register",
    "summary": "Extract data from odoo to create shareholder register",
    "category": "accounting",
    "version": "12.0.1.0.1",
    "author": "Commown SCIC",
    "license": "AGPL-3",
    "website": "https://commown.coop",
    "depends": [
        "account",
        "base_company_extension",
        "report_py3o",
        "mass_mailing",
    ],
    "data": [
        "data/shareholder_tags_update.xml",
        "report/report.xml",
        "views/register.xml",
        "views/res_company.xml",
        "views/shareholder_tags_update.xml",
    ],
    "installable": True,
}
