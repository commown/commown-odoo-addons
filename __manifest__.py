# coding: utf-8
# Copyright (C) 2020 - Today: Commown (https://commown.coop)
# @author: Florent Cayré
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Contract emails",
    "category": "",
    "version": "10.0.1.1.0",
    "author": "Commown SCIC SAS",
    "license": "AGPL-3",
    "website": "https://commown.coop",
    "depends": [
        "contract",
        "mail",
    ],
    "data": [
        "data/cron.xml",
        "security/ir.model.access.csv",
        "views/contract.xml",
        "views/planned_mail_template.xml",
    ],
    "installable": True,
    "application": False,
}
