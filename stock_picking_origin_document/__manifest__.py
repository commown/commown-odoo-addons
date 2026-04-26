# Copyright 2026 Commown SCIC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)

{
    "name": "Stock picking origin document",
    "summary": "Adds an origin document reference to stock pickings",
    "version": "16.0.1.0.0",
    "development_status": "Alpha",
    "category": "Inventory/Delivery",
    "website": "https://github.com/commown/commown-odoo-addons",
    "author": "Commown SCIC",
    "maintainers": ["fcayre", "Honeyxilia"],
    "license": "AGPL-3",
    "depends": [
        "base_origin_document",
        "stock",
    ],
    "data": [
        "view/stock_picking.xml",
    ],
}
