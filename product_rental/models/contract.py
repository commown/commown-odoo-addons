from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


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

    # Add modification behaviour to recurring_next_date
    recurring_next_date = fields.Date(
        inverse='_inverse_recurring_next_date',
    )

    def _inverse_recurring_next_date(self):
        """Allow modification of the next recurring date

        ... if no invoice with a date later than the new next date exists
        (even draft one may be aggregated and invoiced, so we really need
         no invoice past that date).

        In that case, set the next date and reset the last_date_invoiced
        of each line.

        """
        for record in self:
            if self.env["account.invoice.line"].search_count([
                ("contract_line_id", "in", record.contract_line_ids.ids),
                ("invoice_id.date_invoice", ">=", record.recurring_next_date),
            ]):
                raise ValidationError(
                    "There are invoices past the new next recurring date."
                    " Please remove them before."
                )

            last_date_invoiced = max(
                record._get_related_invoices().mapped("date_invoice")
                + [record.date_start])

            for cline in record.contract_line_ids:
                # Update last_date_invoiced first to avoid model constraint
                cline.last_date_invoiced = last_date_invoiced
                cline.recurring_next_date = record.recurring_next_date

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
