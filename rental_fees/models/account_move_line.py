from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    fees_definition_id = fields.Many2one(
        "rental_fees.definition",
        string="Rental fees definition",
        copy=False,
    )
