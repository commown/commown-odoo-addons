# Copyright 2026 Commown SCIC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)

{
    "name": "Mail thread - Redirect messages to mail channels",
    "summary": "Redirect messages from various records using mail.thread towards mail.channel records.",
    "version": "16.0.1.0.1",
    "development_status": "Alpha",
    "category": "Uncategorized",
    "website": "https://github.com/commown/commown-odoo-addons",
    "author": "Commown SCIC",
    "maintainers": ["fcayre", "Honeyxilia"],
    "license": "AGPL-3",
    "depends": [
        "mail",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/mail_thread_redirect.xml",
    ],
}
