# Copyright (C) 2022-today: Commown (https://commown.coop)
# @author: Luc Parent
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


{
    "name": "Commown B2B mail channel",
    "summary": "Commown features related to B2B mail channels",
    "category": "Business",
    "version": "16.0.1.0.0",
    "author": "Commown SCIC",
    "license": "AGPL-3",
    "website": "https://github.com/commown/commown-odoo-addons",
    "depends": ["commown_user_roles", "contract", "mail"],
    "data": [
        "data/ir_config_parameter.xml",
        "views/res_partner.xml",
        "views/mail_channel.xml",
    ],
    "installable": True,
}
