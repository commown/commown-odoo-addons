from odoo import fields, models


class SelfTroubleshootingCategory(models.Model):
    _name = "commown_self_troubleshooting.category"
    _description = "Self troubleshooting category"

    _order = "sequence, id"

    sequence = fields.Integer()
    name = fields.Char(translate=True)


class SelfTroubleshootingItem(models.Model):
    _name = "commown_self_troubleshooting.item"
    _description = "Self troubleshooting item"
    _order = "category_sequence, category_id, sequence, id"

    category_id = fields.Many2one(
        comodel_name="commown_self_troubleshooting.category",
        string="Category",
        required=True,
    )

    category_sequence = fields.Integer(
        related="category_id.sequence",
        string="Category sequence",
        store=True,
    )

    sequence = fields.Integer()

    # Translatable link, URL included as it may lead to a different page per language
    link_url = fields.Char(
        "Link URL",
        help="Target link URL - only required when not a self troubleshooting web page",
        translate=True,
    )
    link_text = fields.Char(
        "Link text",
        help="only required when not a self troubleshooting web page",
        translate=True,
    )

    website_page_id = fields.Many2one(
        comodel_name="website.page",
        string="Website page",
        domain=[("url", "=like", "/page/self-troubleshoot-%")],
        help=(
            "If present item is related to a self troubleshooting web page"
            " that aims at creating a project task, set this field to the web page."
        ),
    )

    requires_contract = fields.Boolean()
    contract_domain = fields.Char(
        "Contract domain",
        help=(
            "Domain used to propose suitable contracts to the partner."
            " It will be concatenated with a fixed one which further"
            " restricts the choices to partner's running contracts."
        ),
    )
