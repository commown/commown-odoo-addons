import logging

from odoo import http
from odoo.http import request

from odoo.addons.website_sale.controllers.main import WebsiteSale

_logger = logging.getLogger(__name__)


class WebsiteSaleB2B(WebsiteSale):
    BIG_PRODUCT_QTY = 100000

    def get_attribute_value_ids(self, product):
        """When in B2B, return prices without taxes. This is a duplication of
        website_sale controller method but replacing website_public_price by
        lst_price for B2B products.
        """

        _logger.debug("In WebsiteSaleB2B.get_attribute_value_ids, product %s", product)
        if product.is_b2b():
            _logger.info("Displaying product in B2B mode: %r", product.name)
            quantity = product._context.get("quantity") or 1
            product = product.with_context(quantity=quantity)

            visible_attrs_ids = (
                product.attribute_line_ids.filtered(lambda l: len(l.value_ids) > 1)
                .mapped("attribute_id")
                .ids
            )
            to_currency = request.website.get_current_pricelist().currency_id
            res = []
            for variant in product.product_variant_ids:
                if to_currency != product.currency_id:
                    lst_price = (
                        variant.currency_id.compute(variant.lst_price, to_currency)
                        / quantity
                    )
                else:
                    lst_price = variant.lst_price / quantity
                visible_attribute_ids = [
                    v.id
                    for v in variant.attribute_value_ids
                    if v.attribute_id.id in visible_attrs_ids
                ]
                res.append(
                    [variant.id, visible_attribute_ids, variant.price, lst_price]
                )
        else:
            res = super(WebsiteSaleB2B, self).get_attribute_value_ids(product)
        return res

    @http.route(
        ["/shop/submit_order"], type="http", auth="public", website=True, sitemap=False
    )
    def submit_order(self, **post):
        "Called by big b2b quotation request button on the online shop"

        # Empty cart
        request.session.update(
            {
                "sale_order_id": False,
                "website_sale_current_pl": False,
                "sale_last_order_id": False,
            }
        )
        request.website.env.user.partner_id.last_website_so_id = False
        request.website.sale_get_order(force_create=True)

        # Create opportunity
        order = request.env["sale.order"].sudo().browse(int(post["order_id"]))
        order.create_b2b_opportunity()

        # Display confirmation page
        return request.render("website_sale_b2b.order_submitted", {"order": order})

    @http.route()
    def product(self, product, category="", search="", **kwargs):
        """Compute default add_qty as minimum to get the lowest unit price
        and complete the render context with rental quantities informations
        (quantity of devices taken into account in the price and reason for it).
        """

        rental_infos = {"reason": None, "quantity": 0.0}

        env = request.env
        if request.website == env.ref("website_sale_b2b.b2b_website"):

            partner = env.user.partner_id.commercial_partner_id
            if partner != env.user.partner_id:

                pl = request.website.get_current_pricelist()
                rental_infos = pl._rented_quantity_infos(product, partner)

                if "add_qty" not in kwargs:
                    _rid = pl._compute_price_rule(
                        [(product, self.BIG_PRODUCT_QTY, partner)]
                    )[product.id][1]
                    if _rid:
                        best_rule = env["product.pricelist.item"].browse(_rid)
                        kwargs["add_qty"] = (
                            best_rule.min_quantity - rental_infos["quantity"]
                        )

        result = super().product(product, category, search, **kwargs)
        result.qcontext["rental_infos"] = rental_infos
        return result
