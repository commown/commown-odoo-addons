# Copyright 2025 Commown SCIC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)

{
    "name": "Commown - Handle Administrative Documents",
    "summary": "Handle download and consultation of administrative documents for portal and internal users.",
    "version": "16.0.1.0.4",
    "development_status": "Beta",
    "category": "Uncategorized",
    "website": "https://github.com/commown/commown-odoo-addons",
    "author": "Commown SCIC",
    "maintainers": ["fcayre", "Honeyxilia"],
    "license": "AGPL-3",
    "depends": [
        "crm",
        "product_rental",
        "commown_res_partner_sms",
        "website_b2b",
    ],
    "external_dependencies": {
        "python": ["magic"],
    },
    "data": [
        "data/actions_crm_lead.xml",
        "data/mail_template.xml",
        "views/res_partner.xml",
        "views/website_portal_templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "/commown_administrative_docs/static/src/js/delete_doc_button.js",
        ]
    },
}
