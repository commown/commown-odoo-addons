# Copyright (C) 2022 - Commown SCIC (https://commown.coop)
# @author: Florent Cayré
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Commown Cooperative campaign",
    "category": "Business",
    "version": "16.0.1.0.1",
    "author": "Commown SCIC",
    "license": "AGPL-3",
    "website": "https://github.com/commown/commown-odoo-addons",
    "external_dependencies": {"python": ["requests", "phonenumbers", "iso8601"]},
    "depends": [
        "commown_contract_variable_discount",
        "queue_job",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/action_coupon.xml",
        "data/ir_config_parameter.xml",
        "data/queue_job_function.xml",
        "views/coupon.xml",
        "views/wizard_late_optin.xml",
    ],
    "installable": True,
}
