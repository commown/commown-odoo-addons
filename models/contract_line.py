from odoo import fields, models, api


class ContractLine(models.Model):
    _inherit = 'contract.line'

    sale_order_line_id = fields.Many2one(
        comodel_name="sale.order.line",
        string="Sale Order Line",
        required=False,
        copy=False,
    )

    commitment_duration = fields.Integer(
        string='Commitment duration',
        help='Commitment duration in recurring interval unit',
    )

    commitment_end_date = fields.Date(
        string='Commitment end date',
        compute='_compute_commitment_end_date', store=True,
    )

    @api.depends('date_start', 'commitment_duration')
    def _compute_commitment_end_date(self):
        for record in self:
            date_delta = self.get_relative_delta(
                record.recurring_rule_type,
                record.commitment_duration*record.recurring_interval)
            record.commitment_end_date = record.date_start + date_delta
