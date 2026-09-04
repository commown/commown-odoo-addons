# Copyright 2025 Commown SCIC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)

{
    "name": "Commown netinstaller gateway",
    "summary": "Netinstaller api module",
    "version": "16.0.1.0.2",
    "development_status": "Alpha",
    "category": "Uncategorized",
    "website": "https://github.com/commown/commown-odoo-addons",
    "author": "Commown SCIC",
    "maintainers": ["fcayre", "Honeyxilia"],
    "license": "AGPL-3",
    "depends": ["product_rental", "stock"],
    "data": [
        "security/ir.model.access.csv",
        "data/netinstaller_post_install_script.xml",
        "views/netinstaller_feature.xml",
        "views/netinstaller_feature_value.xml",
        "views/netinstaller_post_install_script.xml",
        "views/product_views.xml",
        "views/res_partner.xml",
    ],
    "demo": [
        "demo/product_attributes.xml",
        "demo/netinstaller_post_install_script.xml",
        "demo/netinstaller_features.xml",
    ],
}
