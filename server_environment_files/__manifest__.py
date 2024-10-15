# Copyright (C) 2024: Commown (https://commown.coop)
# @author: Luc Parent
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Server configuration environment files for Commown",
    "category": "Tools",
    "version": "12.0.1.0.3",
    "author": "Commown SCIC",
    "license": "AGPL-3",
    "website": "https://commown.coop",
    "depends": [
        "auth_session_timeout",
        "server_environment",
        "server_environment_ir_config_parameter",
        "web",
    ],
    "data": ["views/template.xml"],
    "installable": True,
    "active": False,
}
