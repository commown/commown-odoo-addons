from odoo import fields, models, api, _


class Contract(models.Model):
    _inherit = "contract.contract"

    commitment_period_number = fields.Integer(
        string='Commitment period number',
        help='Commitment duration in number of periods',
        default=0,
        required=True,
    )

    commitment_period_type = fields.Selection(
        [
            ('daily', 'Day(s)'),
            ('weekly', 'Week(s)'),
            ('monthly', 'Month(s)'),
            ('monthlylastday', 'Month(s) last day'),
            ('quarterly', 'Quarter(s)'),
            ('semesterly', 'Semester(s)'),
            ('yearly', 'Year(s)'),
        ],
        default='monthly',
        string='Commitment period type',
        required=True,
    )

    commitment_end_date = fields.Date(
        string="Commitment end date",
        compute="_compute_commitment_end_date", store=True,
    )

    @api.depends("date_start", "commitment_period_number",
                 "commitment_period_type")
    def _compute_commitment_end_date(self):
        delta = self.env["contract.line"].get_relative_delta
        for record in self:
            if record.date_start:
                record.commitment_end_date = record.date_start + delta(
                    record.commitment_period_type,
                    record.commitment_period_number)

    @api.model
    def of_sale(self, sale):
        return self.search([
            ("contract_line_ids.sale_order_line_id.order_id", "=", sale.id),
        ])

    @api.multi
    def action_show_analytic_lines(self):
        self.ensure_one()
        account = self.mapped("contract_line_ids.analytic_account_id").filtered(
            lambda acc: acc.name == self.name)
        if account:
            return {
                "name": _("Cost/Revenue"),
                "type": "ir.actions.act_window",
                "res_model": "account.analytic.line",
                "view_mode": "tree,form,graph,pivot",
                "domain": "[('account_id', '=', %d)]" % account.id,
                "target": "current",
            }
        else:
            return False
