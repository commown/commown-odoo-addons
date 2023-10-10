from odoo import fields, models


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
