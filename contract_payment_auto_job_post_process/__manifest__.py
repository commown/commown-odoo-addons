# Copyright 2025 Commown SCIC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)

{
    "name": "Contract payment automatic in job with post-processing",
    "summary": "This module with automatically pay contract invoices in jobs (like when you install both contract_payment_auto and contract_queue_job), and adds post-processing of the created transaction in each job.",
    "version": "16.0.1.0.2",
    "development_status": "Alpha",
    "category": "Accounting/Payment",
    "website": "https://github.com/commown/commown-odoo-addons",
    "author": "Commown SCIC",
    "maintainers": ["fcayre", "Honeyxilia"],
    "license": "AGPL-3",
    "depends": [
        "contract_payment_auto",
        "contract_queue_job",
    ],
}
