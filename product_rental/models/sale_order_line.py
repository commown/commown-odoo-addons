import logging

from odoo import models
from odoo.tools.float_utils import float_is_zero

_logger = logging.getLogger(__name__)


class ProductRentalSaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def compute_recurrent_payment_amount(self, without_tax=False):
        "Return the rental recurring amount with (by default) or without tax"
        self.ensure_one()

        ratio = self.product_id.list_price / self.product_id.recurrent_payment_amount

        # When product's list_price is explicitly set to 0, the extra amounts set on the
        # attributes (included in lst_price) are interpreted as recurrent payment extra
        # amounts, so we use the product template's recurrent amount plus the lst_price:
        if float_is_zero(ratio, precision_rounding=0.001):
            price = self.product_id.recurrent_payment_amount + self.product_id.lst_price
            recurrent_payment_amount = price * (1 - (self.discount or 0.0) / 100.0)
        else:
            recurrent_payment_amount = (
                self.price_unit * (1 - (self.discount or 0.0) / 100.0) / ratio
            )

        if without_tax:
            taxes = self.product_id.product_tmpl_id.recurrent_payment_tax_ids
            recurrent_payment_amount = taxes.compute_all(recurrent_payment_amount)[
                "total_excluded"
            ]

        return recurrent_payment_amount

    def create_contract_line(self, contract):
        "v12 API must no more be called, see order's action_create_contract"
        _logger.error("Order line create_contract_line must not be called!")
        return self.env["contract.line"]
