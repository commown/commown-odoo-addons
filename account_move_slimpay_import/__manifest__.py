# -*- coding: utf-8 -*-
# Copyright 2018 Commown (https://commown.fr).
# @author Florent Cayré <florent@commown.fr>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Account Move Slimpay Import",
    "summary": "Import Slimpay payment reports",
    "version": "10.0.1.1.0",
    "category": "Finance",
    "website": "https://commown.fr",
    'author': "Commown,Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "external_dependencies": {
        "python": [],
        "bin": [],
    },
    "depends": [
        "account_move_base_import",
    ],
    "data": [
    ],
    "demo": [
    ],
    "qweb": [
    ]
}
