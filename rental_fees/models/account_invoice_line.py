from odoo import fields, models


class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    fees_definition_id = fields.Many2one(
        "rental_fees.definition",
        string="Rental fees definition",
        copy=False,
    )
