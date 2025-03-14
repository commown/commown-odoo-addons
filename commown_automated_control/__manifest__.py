# Copyright (C) 2024: Commown (https://commown.coop)
# @author: Luc Parent
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Commown automated controls",
    "category": "Technical",
    "version": "12.0.1.0.3",
    "author": "Commown SCIC",
    "license": "AGPL-3",
    "website": "https://commown.coop",
    "depends": [
        "base_automation",
        "project",
        "crm",
        "queue_job",
        "web_notify",
    ],
    "data": [
        "security/groups.xml",
        "security/ir.model.access.csv",
        "views/automated_control.xml",
        "views/base_automation.xml",
    ],
    "installable": True,
}
