import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class RentalProductTemplate(models.Model):
    _inherit = "product.template"

    has_recurrent_payment = fields.Boolean(
        "Has recurrent payment",
    )

    is_deposit = fields.Boolean("Is initial payment a deposit", default=True)

    recurrent_payment_amount = fields.Float(
        "Recurrent payment amount",
        digits="Product Price",
    )

    recurrent_payment_frequency = fields.Selection(
        [
            ("daily", "Daily"),
            ("weekly", "Weekly"),
            ("monthly", "Monthly"),
            ("yearly", "Yearly"),
        ],
        "Recurrent payment frequency",
        default="monthly",
        required=True,
    )

    recurrent_payment_tax_ids = fields.Many2many(
        comodel_name="account.tax",
        string="Recurrent payment taxes",
        domain=[("type_tax_use", "=", "sale")],
    )

    def recurrent_payment_amount_ratio(self):
        self.ensure_one()
        return self.has_recurrent_payment and (
            (self.list_price or 1) / self.recurrent_payment_amount
        )

    @api.onchange("is_contract")
    def onchange_is_contract(self):
        if self.is_contract:
            self.has_recurrent_payment = True
