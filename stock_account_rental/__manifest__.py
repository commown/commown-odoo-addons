# Copyright 2024 Commown <contact@commown.coop>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Stock account rental",
    "summary": "Disable stock valuation for rental assets",
    "version": "12.0.1.0.0",
    "development_status": "Alpha",
    "category": "Warehouse",
    "website": "https://commown.coop",
    "author": "Commown SCIC",
    "maintainers": ["fcayre"],
    "license": "AGPL-3",
    "depends": [
        "stock_account",
    ],
    "data": [
        "data/stock_location.xml",
        "data/stock_picking_type.xml",
    ],
    "installable": True,
}
