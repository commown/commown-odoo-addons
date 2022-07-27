import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__file__)


class Contract(models.Model):
    _inherit = "contract.contract"

    commitment_period_number = fields.Integer(
        string="Commitment period number",
        help="Commitment duration in number of periods",
        default=0,
        required=True,
    )

    commitment_period_type = fields.Selection(
        [
            ("daily", "Day(s)"),
            ("weekly", "Week(s)"),
            ("monthly", "Month(s)"),
            ("monthlylastday", "Month(s) last day"),
            ("quarterly", "Quarter(s)"),
            ("semesterly", "Semester(s)"),
            ("yearly", "Year(s)"),
        ],
        default="monthly",
        string="Commitment period type",
        required=True,
    )

    commitment_end_date = fields.Date(
        string="Commitment end date",
        compute="_compute_commitment_end_date",
        store=True,
    )

    date_start = fields.Date(inverse="_inverse_date_start")

    recurring_next_date = fields.Date(inverse="_inverse_recurring_next_date")

    def _inverse_date_start(self):
        "Allow the direct modification of the start date"
        for record in self:
            for cline in record.contract_line_ids:
                cline.date_start = record.date_start
                cline._onchange_date_start()

    def _inverse_recurring_next_date(self):
        """Allow the direct modification of the next recurring date

        ... if no invoice with a date later than the new next date exists
        (even draft one may be aggregated and invoiced, so we really need
         no invoice past that date).

        In that case, set the next date and reset the last_date_invoiced
        of each line.

        """
        force = self._context.get("force_recurring_next_date", False)

        for record in self:
            new_date = record.recurring_next_date
            active_invlines = self.env["account.invoice.line"].search_count(
                [
                    ("contract_line_id", "in", record.contract_line_ids.ids),
                    ("invoice_id.date_invoice", ">=", new_date),
                    ("invoice_id.state", "!=", "cancel"),
                ]
            )
            if not force and active_invlines:
                raise ValidationError(
                    "There are invoices past the new next recurring date."
                    " Please remove them before."
                )

            inv_dates = (
                record._get_related_invoices()
                .filtered(lambda inv: inv.state != "cancel")
                .mapped("date_invoice")
            )
            last_date_invoiced = inv_dates and max(inv_dates) or False

            if force and last_date_invoiced and last_date_invoiced >= new_date:
                real_last_date_invoiced = last_date_invoiced
                last_date_invoiced = max(
                    [d for d in inv_dates if d < new_date] + [record.date_start]
                )
                _logger.warning(
                    "Forcing last_date_invoiced to %s although last invoice"
                    " date is %s",
                    last_date_invoiced,
                    real_last_date_invoiced,
                )

            _logger.info(
                "Setting all contract %s lines last_date_invoiced"
                " to %s and recurring_next_date to %s",
                record.name,
                last_date_invoiced,
                new_date,
            )

            for cline in record.contract_line_ids:
                # Update last_date_invoiced first to avoid model constraint
                cline.last_date_invoiced = last_date_invoiced
                cline.recurring_next_date = new_date

    @api.depends("date_start", "commitment_period_number", "commitment_period_type")
    def _compute_commitment_end_date(self):
        delta = self.env["contract.line"].get_relative_delta
        for record in self:
            if record.date_start:
                record.commitment_end_date = record.date_start + delta(
                    record.commitment_period_type, record.commitment_period_number
                )

    @api.model
    def of_sale(self, sale):
        return self.search(
            [
                ("contract_line_ids.sale_order_line_id.order_id", "=", sale.id),
            ]
        )

    @api.multi
    def action_show_analytic_lines(self):
        self.ensure_one()
        account = self.mapped("contract_line_ids.analytic_account_id").filtered(
            lambda acc: acc.name == self.name
        )
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
