from odoo import fields, models


class PaymentIssuesContract(models.Model):
    _inherit = "contract.contract"

    payment_issue_ids = fields.One2many(
        comodel_name="project.task",
        compute="_compute_payment_issues",
        string="Payment issues",
    )

    def _compute_payment_issues(self):
        for record in self:
            record.payment_issue_ids = self.env["project.task"].search(
                [("invoice_id", "in", record._get_related_invoices().ids)]
            )
