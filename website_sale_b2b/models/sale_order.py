import logging

from odoo import _, api, fields, models

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

    name = fields.Text(compute="_recompute_name", store=True)

    def display_rental_price(self, amount=None):
        """Format current line's product rental price in the order partner's language
        or given amount if specified.

        If the product is b2b, append (translated) excluding taxes text to the currency.
        """

        if amount is None:
            amount = self.compute_rental_price(None)
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

    def templated_description_sale(self, with_prefix=True):
        """Return a description sale of current line, w/ or w/o its product name prefix

        If the line's product has a templated description_sale, it is evaluated as a
        mako template before returning the result.
        """
        descr = False
        product = self.product_id

        if product:
            if with_prefix:
                descr = self.get_sale_order_line_multiline_description_sale(product)
            else:
                descr = product.description_sale

            if product.description_sale_is_template:
                descr = mako_template_env.from_string(descr).render(
                    {"record": self.with_context(lang=self.order_partner_id.lang)}
                )

        return descr

    @api.depends("price_unit", "product_id")
    def _recompute_name(self):
        """Update the name (=description) on price_unit and product change if
        it is a jinja template.

        In the v12 backend UI this is far from perfect, as the
        description is first loaded when the product is set but the
        price is not yet computed so the loaded description is wrong
        at first, but then correct.

        We use a computed field here to make sure the name is updated
        when using the `write` method too. A simple use case that
        defeats other approaches is a user that puts a templated
        description_sale product in its basket.
        """
        for record in self:
            record.name = record.templated_description_sale()
