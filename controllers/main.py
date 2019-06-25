import logging

from odoo.http import request

from odoo.addons.website_sale.controllers.main import WebsiteSale


_logger = logging.getLogger(__name__)


class WebsiteSaleB2B(WebsiteSale):

    def get_attribute_value_ids(self, product, category=None):
        """ When in B2B, return prices without taxes. This is a duplication of
        website_sale controller method but replacing website_public_price by
        lst_price for B2B products.
        """

        _logger.debug('In WebsiteSaleB2B.get_attribute_value_ids')
        if category and category.is_b2b():
            _logger.info('Displaying product in B2B mode: %r', product.name)
            quantity = product._context.get('quantity') or 1
            product = product.with_context(quantity=quantity)

            visible_attrs_ids = product.attribute_line_ids.filtered(
                lambda l: len(l.value_ids) > 1).mapped('attribute_id').ids
            to_currency = request.website.get_current_pricelist().currency_id
            res = []
            for variant in product.product_variant_ids:
                if to_currency != product.currency_id:
                    lst_price = variant.currency_id.compute(
                        variant.lst_price, to_currency) / quantity
                else:
                    lst_price = variant.lst_price / quantity
                visible_attribute_ids = [
                    v.id for v in variant.attribute_value_ids
                    if v.attribute_id.id in visible_attrs_ids]
                res.append([
                    variant.id,
                    visible_attribute_ids,
                    variant.price, lst_price])
        else:
            res = super(WebsiteSaleB2B, self).get_attribute_value_ids(product)
        return res
