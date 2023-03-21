# Copyright 2023 Commown <contact@commown.coop>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Payment Token Uniquify",
    "summary": "Module summary",
    "version": "12.0.1.0.1",
    "development_status": "Alpha",
    "category": "Payment",
    "website": "https://commown.coop",
    "author": "Commown SCIC",
    "maintainers": ["fcayre"],
    "license": "AGPL-3",
    "depends": [
        "payment",
        "queue_job",
    ],
    "data": [
        "data/obsolescence_action.xml",
        "security/ir.model.access.csv",
        "views/payment_acquirer.xml",
        "views/res_partner.xml",
    ],
    "installable": True,
}
