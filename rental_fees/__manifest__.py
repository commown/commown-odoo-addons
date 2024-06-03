{
    "name": "rental_fees",
    "category": "Business",
    "summary": "Commown module to compute fees to be paid to its device suppliers",
    "version": "12.0.2.0.16",
    "description": """
        Commown module to compute fees to be paid to its device suppliers.
    """,
    "author": "Commown SCIC",
    "license": "AGPL-3",
    "website": "https://commown.coop",
    "depends": [
        "commown_devices",
        "commown_contract_forecast",
        "purchase",
        "queue_job",
        "report_py3o",
        "account_usability",  # for the invoice line's date_invoice field
        "contract_auto_merge_invoice",
        "web_notify",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/actions.xml",
        "data/mail_template.xml",
        "views/rental_fees_computation.xml",
        "views/rental_fees_definition.xml",
        "views/rental_fees_report.xml",
    ],
}
