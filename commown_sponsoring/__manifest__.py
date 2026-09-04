# Copyright 2026 Commown SCIC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)

{
    "name": "Commown - Sponsoring campaigns",
    "summary": "Handles a sponsoring through user-assigned coupon campaigns",
    "version": "16.0.1.0.0",
    "development_status": "Alpha",
    "category": "Uncategorized",
    "website": "https://github.com/commown/commown-odoo-addons",
    "author": "Commown SCIC",
    "maintainers": ["fcayre", "Honeyxilia"],
    "license": "AGPL-3",
    "depends": [
        "product_rental",
        "website_sale_coupon",
    ],
    "data": [
        "data/actions_server.xml",
        "data/base_automation.xml",
        "data/ir_config_parameter.xml",
        "data/mail_templates.xml",
        "views/customer_portal_templates.xml",
        "views/view_campaign.xml",
        "views/view_res_partner.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "/commown_sponsoring/static/src/js/sponsor_code_copy.esm.js",
            "/commown_sponsoring/static/src/js/website_sale_coupon.esm.js",
        ]
    },
}
