# Copyright 2022-today Commown SCIC (https://commown.coop)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Slimpay Payment base",
    "summary": "Provides server to server implementation of Slimpay payment",
    "version": "16.0.1.0.0",
    "development_status": "Beta",
    "category": "Accounting",
    "website": "https://github.com/commown/commown-odoo-addons",
    "author": "Commown SCIC",
    "maintainers": ["fcayre"],
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "external_dependencies": {
        "python": ["coreapi", "hal_codec", "iso8601", "phonenumbers"]
    },
    "depends": [
        "payment",
        "partner_firstname",
        "base_phone",
    ],
    "data": [
        "views/payment_views.xml",
        "views/payment_slimpay_templates.xml",
        "data/payment_acquirer_data.xml",
    ],
}
