import datetime

from odoo import fields, models
from odoo.tools.safe_eval import safe_eval


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

    def name_get(self):
        result = []
        for record in self:
            name = record.website_page_id.display_name or record.link_text
            result.append((record.id, name))
        return result

    def get_contracts(self, partner):
        "Return the possible contract resultset for current item (may be empty)"
        self.ensure_one()

        contracts = self.env["contract.contract"]

        if self.requires_contract:
            today = datetime.date.today()
            domain = [
                (
                    "partner_id.commercial_partner_id",
                    "=",
                    partner.commercial_partner_id.id,
                ),
                ("date_start", "<=", today),
                "|",
                ("date_end", "=", False),
                ("date_end", ">", today),
            ]

            if self.contract_domain:
                domain += safe_eval(
                    self.contract_domain,
                    {"env": self.env, "datetime": datetime, "base_domain": domain},
                )

            contracts = self.env["contract.contract"].search(domain)

        return contracts

    def get_link(self):
        """Return link details according to website_page_id being set or not

        When set, return the page details, else return current link field values.

        The return value is a dict of the form:
        {"category": <str>, "url": <str>, "text": <str>}
        """
        self.ensure_one()

        page = self.website_page_id
        return {
            "category": self.category_id.name,
            "url": page.url if page else self.link_url,
            "text": page.website_meta_description if page else self.link_text,
        }
