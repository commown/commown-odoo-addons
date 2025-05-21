# Copyright 2023 Commown <contact@commown.coop>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Payment Token Uniquify",
    "summary": "Module summary",
    "version": "16.0.1.0.0",
    "development_status": "Alpha",
    "category": "Payment",
    "website": "https://github.com/commown/commown-odoo-addons",
    "author": "Commown SCIC",
    "maintainers": ["fcayre"],
    "license": "AGPL-3",
    "depends": [
        "payment",
        "contract_payment_auto",
        "queue_job",
    ],
    "data": [
        "data/obsolescence_action.xml",
        "security/ir.model.access.csv",
        "views/payment_provider.xml",
    ],
    "installable": True,
}
