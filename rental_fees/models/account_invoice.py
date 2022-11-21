from odoo import fields, models


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    fees_computation_id = fields.Many2one(
        "rental_fees.computation",
        string="Rental fees computation",
        copy=False,
    )
