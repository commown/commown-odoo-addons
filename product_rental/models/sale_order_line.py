import logging
from datetime import date

from odoo import api, models


_logger = logging.getLogger(__name__)


CONTRACT_PROD_MARKER = '##PRODUCT##'
CONTRACT_ACCESSORY_MARKER = '##ACCESSORY##'
NO_DATE = date(2030, 1, 1)


def _gen_contract_lines(so_line, contract, rental_products):
    """Use contract_template to generate (yield) contract lines, with
    following conventions:

    - the contract template line which name contains ##PRODUCT## is
      used as a model for the rental product line described in
      `rental_products` dict value which key is ##PRODUCT##

    - the contract template line which name contains ##ACCESSORY## is
      used as a model for the rental product lines described in
      `rental_products` dict value which key is ##ACCESSORY##

    - other contract template lines generate normal contract lines

    Contract lines that are not marked as main or accessory are
    associated to the give sale order line `so_line`.

    """
    for line in contract.contract_line_ids:
        for marker, products in rental_products.items():
            if marker in line.name:
                for product, so_line, quantity in products:
                    line_copy = line.copy({
                        'name': line.name.replace(marker, product.name),
                        'specific_price': so_line.compute_rental_price(
                            line.product_id.taxes_id),
                        'quantity': quantity,
                        'sale_order_line_id': so_line.id,
                    })
                    yield line_copy
                # Remove marked line once it was used
                line.cancel()
                line.unlink()
                break
        else:
            line.sale_order_line_id = so_line.id
            yield line


def _rental_products(so_line, acc_by_so_line):
    " Helper function to prepare data required for contract line generation "
    _acs = acc_by_so_line[so_line]
    __acs = [(p, l, l.product_uom_qty) for (p, l) in set(_acs)]
    qtty = so_line.product_uom_qty

    return {
        CONTRACT_PROD_MARKER: [(so_line.product_id, so_line, qtty)],
        CONTRACT_ACCESSORY_MARKER: sorted(__acs, key=lambda a: a[0].id),
    }


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
        return self.env['contract.line']

    @api.model
    def _product_rental_create_contract_line(
            self, contract, contract_descr):
        """Return contract lines from given contract template and products.

        See `_gen_contract_lines` docstring for more details.
        """
        contract_lines = self.env['contract.line']
        sequence = 0
        so_line = contract_descr['so_line']  # main product so line
        order = so_line.order_id
        products = _rental_products(contract_descr)

        for contract_line in _gen_contract_lines(so_line, contract, products):
            sequence += 1
            contract_line.update({
                'sequence': sequence,
                'analytic_account_id': order.analytic_account_id.id,
                'recurring_next_date': NO_DATE,
            })
            contract_line.date_start = NO_DATE
            contract_line._onchange_date_start()
            contract_lines |= contract_line

        return contract_lines


def _rental_products(contract_descr):
    " Helper function to prepare data required for contract line generation "
    so_line = contract_descr['so_line']
    _acs = contract_descr['accessories']
    __acs = [(p, l, 1) for (p, l) in set(_acs)]

    return {
        CONTRACT_PROD_MARKER: [(so_line.product_id, so_line, 1)],
        CONTRACT_ACCESSORY_MARKER: sorted(__acs, key=lambda a: a[0].id),
    }
