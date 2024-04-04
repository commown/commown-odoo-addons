import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class ProductRentalSaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def compute_rental_price(self, without_tax=False):
        "Return the rental recurring amount with (by default) or without tax"
        self.ensure_one()
        ratio = self.product_id.list_price / self.product_id.rental_price
        rental_price = self.price_unit * (1 - (self.discount or 0.0) / 100.0) / ratio
        if without_tax:
            taxes = self.product_id.product_tmpl_id.rental_tax_ids
            rental_price = taxes.compute_all(rental_price)["total_excluded"]
        return rental_price

    @api.multi
    def create_contract_line(self, contract):
        "v12 API must no more be called, see order's action_create_contract"
        _logger.error("Order line create_contract_line must not be called!")
        return self.env["contract.line"]
