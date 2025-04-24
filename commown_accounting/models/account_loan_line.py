from odoo import fields, models


class AccountLoanLine(models.Model):
    _inherit = "account.loan.line"

    loan_start_date = fields.Date(
        string="Loan start date",
        related="loan_id.start_date",
        store=True,
    )
