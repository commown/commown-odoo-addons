import logging

from odoo import api, fields, models

import odoo.addons.decimal_precision as dp

_logger = logging.getLogger(__name__)


class RentalProductTemplate(models.Model):
    _inherit = "product.template"

    has_recurrent_payment = fields.Boolean("Is rental product")

    is_deposit = fields.Boolean("Is initial payment a deposit", default=True)

    recurrent_payment_amount = fields.Float(
        "Rental price", dp.get_precision("Product Price")
    )

    recurrent_payment_frequency = fields.Selection(
        [
            ("daily", "Daily"),
            ("weekly", "Weekly"),
            ("monthly", "Monthly"),
            ("yearly", "Yearly"),
        ],
        "Rental payment frequency",
        default="monthly",
        help="Frequency of the rental price payment",
        required=True,
    )

    recurrent_payment_tax_ids = fields.Many2many(
        comodel_name="account.tax",
        string="Rental taxes",
        domain=[("type_tax_use", "=", "sale")],
    )

    @api.multi
    def recurrent_payment_amount_ratio(self):
        self.ensure_one()
        return self.has_recurrent_payment and (
            (self.list_price or 1) / self.recurrent_payment_amount
        )
