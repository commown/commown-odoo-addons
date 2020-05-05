import logging

from odoo import api, models


_logger = logging.getLogger(__name__)

CONTRACT_PROD_MARKER = '##PRODUCT##'
CONTRACT_ACCESSORY_MARKER = '##ACCESSORY##'


def rental_product_price(product, partner):
    while partner.parent_id:
        partner = partner.parent_id
    tax = partner.property_account_receivable_id.tax_ids
    to_excl = 1. / (1. + tax.amount / 100.)
    ratio = product.list_price / product.rental_price
    return (product.website_public_price * to_excl / ratio)


class ProductRentalAccountAnalyticAccount(models.Model):
    _inherit = "account.analytic.account"

    @api.multi
    def _convert_contract_lines(self, contract):
        """Extend contract functionalities: have ability to gather a main
        rental product and its (also rented) accessories on the same
        contract.

        This is done using dedicated markers (##PRODUCT## and
        ##ACCESSORY##) in recurring invoice line names. Those lines
        will be used as templates: the marker in the name is replaced
        by the name of the corresponding article, the quantity is set
        to 1 and the price set to the rental price of the product.
        """
        new_lines = super(ProductRentalAccountAnalyticAccount,
                          self)._convert_contract_lines(contract)

        sale_context = self.env.context.get('contract_from_so')
        if not sale_context:
            return new_lines

        contract_lines = []
        partner = contract.partner_id
        rental_products = {
            CONTRACT_PROD_MARKER: [
                (sale_context['main_product'], sale_context['main_so_line'], 1)
            ],
            CONTRACT_ACCESSORY_MARKER: sale_context['accessories'],
        }

        _logger.debug('rental_products: %s', rental_products)

        for new_line in new_lines:
            for marker, products in rental_products.items():
                if marker in new_line[2]['name']:
                    for product, so_line, qtty in products:
                        vals = new_line[2].copy()
                        vals.update({
                            'name': vals['name'].replace(
                                marker, product.display_name),
                            'specific_price': rental_product_price(
                                product, partner),
                            'qtty': qtty,
                            'sale_order_line_id': so_line.id,
                        })
                        vals['display_name'] = vals['name']
                        # avoid inverse price computation
                        if 'price_unit' in vals:
                            del vals['price_unit']
                        contract_lines.append((0, 0, vals))
                    break
            else:
                new_line[2]['sale_order_line_id'] = sale_context[
                    'main_so_line'].id
                contract_lines.append(new_line)

        return contract_lines
