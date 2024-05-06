import logging

from odoo import _, api, models

from odoo.addons.mail.models.mail_template import format_amount, mako_template_env

_logger = logging.getLogger(__file__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def create_b2b_opportunity(self):
        """Called when a big b2b customer submits an order request online

        An opportunity is created in the big_b2b_team commercial team.
        """

        self.ensure_one()
        _logger.info("Received big B2B order request for %s", self.name)

        team = self.env.ref("website_sale_b2b.big_b2b_team")
        stage = self.env.ref("website_sale_b2b.big_b2b_stage_new")
        company_name = self.partner_id.commercial_company_name or "?"
        lead = self.env["crm.lead"].create(
            {
                "name": "%s / %s" % (self.name, company_name),
                "partner_id": self.partner_id.id,
                "type": "opportunity",
                "team_id": team.id,
                "stage_id": stage.id,
                "so_line_id": self.order_line and self.order_line[0].id,
            }
        )
        # Override post-create behaviour that auto-assigns team and stage
        lead.update({"team_id": team.id, "stage_id": stage.id})
        return lead

    @api.multi
    def action_quotation_send(self):
        result = super().action_quotation_send()
        ref = self.env.ref
        if result["context"][
            "default_use_template"
        ] and self.partner_id.website_id == ref("website_sale_b2b.b2b_website"):
            b2b_template = ref("website_sale_b2b.email_template_edi_sale")
            result["context"]["default_template_id"] = b2b_template.id
        return result


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def display_rental_price(self, amount=None):
        """Format current line's product rental price in the order partner's language
        or given amount if specified.

        If the product is b2b, append (translated) excluding taxes text to the currency.
        """

        if amount is None:
            amount = self.compute_rental_price()
        str_amount = format_amount(self.env, amount, self.product_id.currency_id)

        if self.product_id.product_tmpl_id.is_b2b():
            symbol = self.product_id.currency_id.symbol
            str_amount = str_amount.replace(symbol, symbol + _(" excl. taxes"))

        # Get frequency t10n values from fields_get:
        ftypes = dict(self.product_id.fields_get()["rental_frequency"]["selection"])

        return str_amount + " " + ftypes[self.product_id.rental_frequency]

    def display_commitment_duration(self):
        "Format current product's rental contract commitment duration"

        ct = self.product_id.property_contract_template_id
        rtypes = dict(ct.fields_get()["commitment_period_type"]["selection"])
        unit = rtypes[ct.commitment_period_type].lower()
        return "%d %s" % (ct.commitment_period_number, unit)

    def _render_product_templated_descr(self):
        self.ensure_one()
        descr = self.get_sale_order_line_multiline_description_sale(self.product_id)
        return mako_template_env.from_string(descr).render(
            {"record": self.with_context(lang=self.order_partner_id.lang)}
        )

    @api.onchange("price_unit", "product_id")
    def _onchange_recompute_name(self):
        "Called by UI on listed field change"
        if self.product_id.description_sale_is_template:
            self.name = self._render_product_templated_descr()

    @api.multi
    def write(self, vals):
        result = super().write(vals)
        if (
            "price_unit" in vals or "product_id" in vals
        ) and self.product_id.description_sale_is_template:
            self.name = self._render_product_templated_descr()
        return result
