# Copyright 2022 Commown SCIC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Attachment language",
    "summary": "Add a language field to an attachment",
    "version": "12.0.1.0.0",
    # see https://odoo-community.org/page/development-status
    "development_status": "Alpha",
    "category": "Uncategorized",
    "website": "https://commown.coop",
    "author": "Commown SCIC",
    # see https://odoo-community.org/page/maintainer-role for a description of the maintainer role and responsibilities
    "maintainers": ["fcayre"],
    "license": "AGPL-3",
    "depends": [
        "base",
    ],
    "data": [
        "views/ir_attachment.xml",
    ],
}
