# Copyright 2025 Commown <contact@commown.coop>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Date range for portal users",
    "summary": "Fix read access on date range type for portal users",
    "version": "12.0.1.0.2",
    "development_status": "Alpha",
    "category": "Uncategorized",
    "website": "https://github.com/commown/commown-odoo-addons",
    "author": "Commown SCIC",
    "maintainers": ["Honeyxilia", "fcayre"],
    "license": "AGPL-3",
    "depends": [
        "date_range",
        "portal",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/date_range_security.xml",
    ],
    "installable": True,
}
