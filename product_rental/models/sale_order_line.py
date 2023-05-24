import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class ProductRentalSaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def compute_rental_price(self, rental_taxes):
        "Return the rental recurring amount"
        self.ensure_one()
        ratio = self.product_id.list_price / self.product_id.rental_price
        return self.price_unit * (1 - (self.discount or 0.0) / 100.0) / ratio

    @api.multi
    def create_contract_line(self, contract):
        "v12 API must no more be called, see order's action_create_contract"
        _logger.error("Order line create_contract_line must not be called!")
        return self.env["contract.line"]
