# Copyright 2025 Commown SCIC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)

{
    "name": "Commown - Allow backend passage",
    "summary": "Allow passage to the backend (/web) part of the web client for non-internal users, with limited access",
    "version": "16.0.1.0.0",
    "development_status": "Alpha",
    "category": "Uncategorized",
    "website": "https://github.com/commown/commown-odoo-addons",
    "author": "Commown SCIC",
    "maintainers": ["fcayre", "Honeyxilia"],
    "license": "AGPL-3",
    "depends": [
        "portal",
    ],
    "assets": {
        "web.assets_backend": [
            "/commown_allow_backend_passage/static/src/js/backend_passage_navbar.esm.js",
        ],
    },
}
