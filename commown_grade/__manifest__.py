# Copyright (C) 2024 - Commown (https://commown.coop)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Commown Grade",
    "description": "This modules create grades on lots",
    "category": "stock",
    "version": "16.0.1.0.0",
    "author": "Commown SCIC",
    "license": "AGPL-3",
    "website": "https://github.com/commown/commown-odoo-addons",
    "depends": ["stock", "web_notify"],
    "installable": True,
    "data": [
        "security/groups.xml",
        "security/ir.model.access.csv",
        "data/grade.xml",
        "views/grade.xml",
        "views/grade_history_line.xml",
        "views/stock_lot.xml",
    ],
}
