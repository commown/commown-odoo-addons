import cgi
from collections import defaultdict
from urllib.parse import urlencode

from odoo import _, api, fields, models

EMAIL_RATINGS = [
    ("-1", "No data"),
    ("0", "No mail received"),
    ("1", "Cold"),
    ("2", "Neutral"),
    ("3", "Warm"),
    ("4", "Motivated"),
]

WEBID_RATINGS = [
    ("-1", "No data"),
    ("0", "Known strange"),
    ("1", "Known neutral"),
    ("2", "Known Coherent"),
]

TECHNICAL_SKILLS = [
    ("-1", "No data"),
    ("0", "neophyte"),
    ("1", "intermediary"),
    ("2", "confirmed"),
]

GLOBAL_FEELING = [
    ("-1", "No data"),
    ("0", "No go"),
    ("1", "Suspicious"),
    ("2", "Medium"),
    ("3", "Pretty good"),
    ("4", "No hesitation"),
]


class CommownCrmLead(models.Model):
    _inherit = "crm.lead"

    so_line_id = fields.Many2one("sale.order.line", "Sale order line")

    contract_id = fields.Many2one("contract.contract", "Contract")

    email_rating = fields.Selection(
        EMAIL_RATINGS, string="Email Rating", default=EMAIL_RATINGS[0][0]
    )
    web_searchurl = fields.Html("Search on the web", compute="_compute_web_searchurl")
    webid_unknown = fields.Boolean("Unknown on the web", default=False)
    webid_rating = fields.Selection(
        WEBID_RATINGS, string="Web identity Rating", default=WEBID_RATINGS[0][0]
    )
    webid_notes = fields.Text("Notes web")

    sent_collective_email = fields.Boolean("Sent collective email", default=False)
    first_phone_call = fields.Boolean(
        "1st phone call", help="without leaving a message", default=False
    )
    second_phone_call = fields.Boolean(
        "2nd phone call", help="with a message", default=False
    )
    email_boost = fields.Boolean("Email boost sent", default=False)
    third_phone_call = fields.Boolean("3rd phone call", default=False)
    email_ultimatum = fields.Boolean("Email ultimatum", default=False)
    registered_mail_sent = fields.Boolean("Registered mail sent", default=False)

    orders_description = fields.Html(
        "Orders at date", sanitize_attributes=False, compute="_compute_orders_descr"
    )
    initial_data_notes = fields.Text("Notes initiales")
    identity_validated = fields.Boolean("Identity validated", default=False)
    mobile_validated = fields.Boolean("Mobile phone validated", default=False)
    email_validated = fields.Boolean("Email validated", default=False)
    billing_address_validated = fields.Boolean(
        "Billing address validated", default=False
    )
    delivery_address_validated = fields.Boolean(
        "Delivery address validated", default=False
    )
    address_hesitation = fields.Boolean("Address spelling hesitation", default=False)
    technical_skills = fields.Selection(
        TECHNICAL_SKILLS, string="Technical skills", default=TECHNICAL_SKILLS[0][0]
    )
    questions = fields.Text("Customer questions")
    global_feeling = fields.Selection(
        GLOBAL_FEELING, string="Global feeling", default=GLOBAL_FEELING[0][0]
    )
    comments = fields.Text("Comments")
    used_for_risk_analysis = fields.Boolean(
        "Used for risk analysis", related="team_id.used_for_risk_analysis"
    )

    @api.onchange("partner_id")
    def _compute_orders_descr(self):
        "Compute the orders_description of every record in current resultset"

        def ref(xml_id):
            return self.env.ref(f"commown_lead_risk_analysis.{xml_id}")

        orders_tmpl = ref("partner_orders_tmpl")
        products_tmpl = ref("company_product_summary")

        def get_orders(partner):
            return self.env["sale.order"].search(
                [("partner_id", "child_of", partner.id), ("state", "=", "sale")]
            )

        def _product_summary(partner):
            order_lines = (
                get_orders(partner)
                .mapped("order_line")
                .sorted(
                    lambda ol: ol.product_id.product_tmpl_id.property_contract_template_id.name
                    or "",
                    reverse=True,
                )
            )

            summary = defaultdict(float)
            for oline in order_lines:
                summary[oline.product_id.product_tmpl_id] += oline.product_uom_qty

            return products_tmpl.render({"company": partner, "summary": summary})

        for record in self:

            # Possible when changing the partner of the lead in the UI (onchange):
            if not record.partner_id:
                record.orders_description = ""
                continue

            descr = []
            partner = record.partner_id.commercial_partner_id

            descr.append(orders_tmpl.render({"orders": get_orders(partner)}))

            if record.partner_id != partner:
                descr.append(_product_summary(partner))

                holding = record.partner_id.get_holding()
                if holding != partner:
                    descr.append(_product_summary(holding))

            record.orders_description = (b"\n".join(descr)).decode("utf-8")

    @api.multi
    def _compute_web_searchurl(self):
        for lead in self:
            # XXX template me!
            query = (
                " ".join((lead.contact_name or "", lead.city or ""))
                .strip()
                .encode("utf-8")
            )
            url = "http://www.google.fr/search?%s" % urlencode({"q": query})
            lead.web_searchurl = "<a target='_blank' href='%s'>%s</a>" % (
                cgi.escape(url, quote=True),
                cgi.escape(_("Web search link"), quote=True),
            )

    def button_open_sale_order(self):
        self.ensure_one()
        order_id = self.so_line_id.mapped("order_id").id
        if order_id:
            return {
                "type": "ir.actions.act_window",
                "res_model": "sale.order",
                "name": _("Sale Order"),
                "views": [(False, "form")],
                "res_id": order_id,
            }

    def button_open_contract(self):
        contract = self.contract_id
        if contract:
            result = contract.get_formview_action()

            # Fix a bug (in the js engine?) that leads to a UI crash when
            # adding a contract line to the displayed contract: without this,
            # the active_id is the crm lead, and is (erronously) used as the
            # contract id to add contract lines to.
            # Note that the same bug is present in the product_contract module
            # (button calling sale.order's action_show_contracts method)
            result["context"] = {"active_id": contract.id}

            return result
