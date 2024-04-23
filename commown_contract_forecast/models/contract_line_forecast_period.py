from odoo import api, fields, models

from odoo.addons import decimal_precision as dp


class ContractLineForecastPeriod(models.Model):

    _inherit = "contract.line.forecast.period"

    contract_template_id = fields.Many2one(
        comodel_name="contract.template",
        string="Contract template",
        readonly=True,
        related="contract_line_id.contract_id.contract_template_id",
        store=True,
        index=True,
    )

    market = fields.Selection(
        [("B2C", "B2C"), ("B2B", "B2B")],
        string="Market",
        readonly=True,
        compute="_compute_market_and_product_range",
        store=True,
        index=True,
    )

    product_range = fields.Char(
        string="Product range",
        readonly=True,
        compute="_compute_market_and_product_range",
        store=True,
        index=True,
    )

    price_subtotal_taxed = fields.Float(
        digits=dp.get_precision("Account"),
        string="Amount taxed",
        compute="_compute_price_subtotal_taxed",
        store=True,
    )

    @api.multi
    @api.depends("price_subtotal")
    def _compute_price_subtotal_taxed(self):
        for line in self:
            taxes = line.product_id.product_tmpl_id.taxes_id
            prices = taxes.compute_all(line.price_subtotal)
            line.price_subtotal_taxed = prices["total_included"]

    @api.depends("contract_line_id")
    def _compute_market_and_product_range(self):
        for record in self:
            ct_name = record.contract_line_id.contract_id.contract_template_id.name
            if ct_name:
                name_data = ct_name.split("/", 2)
                if len(name_data) >= 2:
                    record.product_range = name_data[0]
                    record.market = "B2C" if name_data[1] == "B2C" else "B2B"
                    continue
            record.product_range = False
            record.market = False
