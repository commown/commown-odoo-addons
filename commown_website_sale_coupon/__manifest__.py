# Copyright 2025 Commown SCIC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)

{
    "name": "Commown Website Sale Coupon",
    "summary": "Add features related to the website_sale_coupon module (coupon file, coupon in sale.order title)",
    "version": "16.0.1.0.0",
    "development_status": "Beta",
    "category": "Uncategorized",
    "website": "https://github.com/commown/commown-odoo-addons",
    "author": "Commown SCIC",
    "maintainers": ["fcayre", "Honeyxilia"],
    "license": "AGPL-3",
    "depends": [
        "attachment_indexation",
        "commown_lead_risk_analysis",
        "website_sale_coupon",
    ],
    "external_dependencies": {
        "bin": ["rsvg-convert"],
    },
}
