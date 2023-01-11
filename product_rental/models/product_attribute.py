from odoo import fields, models

from odoo.addons import decimal_precision as dp


class ProductTemplateAttributeValue(models.Model):
    _inherit = "product.template.attribute.value"

    is_rental = fields.Boolean(
        "Is used by a rental product",
        related="product_tmpl_id.is_rental",
    )

    rental_price_extra = fields.Float(
        string="Extra rental price",
        help="Extra price of the product rent for current variant",
        digits=dp.get_precision("Product Price"),
        compute="_compute_rental_price_extra",
        inverse="_inverse_rental_price_extra",
    )

    def _compute_rental_price_extra(self):
        for ptav in self:
            if ptav.is_rental:
                pt = ptav.product_tmpl_id
                ptav.rental_price_extra = (
                    ptav.price_extra * pt.rental_price / pt.list_price
                )
            else:
                ptav.rental_price_extra = False

    def _inverse_rental_price_extra(self):
        for ptav in self:
            if ptav.is_rental:
                pt = ptav.product_tmpl_id
                ptav.price_extra = (
                    ptav.rental_price_extra * pt.list_price / pt.rental_price
                )
