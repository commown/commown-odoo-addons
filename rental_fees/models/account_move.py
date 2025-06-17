from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    fees_computation_id = fields.Many2one(
        "rental_fees.computation",
        string="Rental fees computation",
        copy=False,
    )
