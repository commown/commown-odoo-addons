# Copyright 2023 Commown SCIC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)

{
    "name": "Commown contract forecast integration",
    "summary": "Integrate the contract_forecast module into Commown odoo-based management software",
    "version": "12.0.1.1.1",
    "development_status": "Alpha",
    "category": "Accounting/Accounting",
    "website": "https://commown.coop",
    "author": "Commown SCIC",
    "maintainers": ["fcayre"],
    "license": "AGPL-3",
    "installable": True,
    "depends": [
        "contract_forecast",
        "commown_cooperative_campaign",
        "contract_queue_job",  # Make tests behave as when the commown module is installed
    ],
    "data": [
        "views/contract_line_forecast_period.xml",
    ],
}
