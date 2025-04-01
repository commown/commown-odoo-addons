from odoo import fields, models

from odoo.addons import decimal_precision as dp


class ProductTemplateAttributeValue(models.Model):
    _inherit = "product.template.attribute.value"

    has_recurrent_payment = fields.Boolean(
        "Is used by a product with a recurrent payment",
        related="product_tmpl_id.has_recurrent_payment",
    )

    recurrent_payment_amount_extra = fields.Float(
        string="Extra rental price",
        help="Extra price of the product rent for current variant",
        digits=dp.get_precision("Product Price"),
        compute="_compute_recurrent_payment_amount_extra",
        inverse="_inverse_recurrent_payment_amount_extra",
    )

    def _compute_recurrent_payment_amount_extra(self):
        for ptav in self:
            if ptav.has_recurrent_payment:
                pt = ptav.product_tmpl_id
                ptav.recurrent_payment_amount_extra = (
                    ptav.price_extra * pt.recurrent_payment_amount / pt.list_price
                )
            else:
                ptav.recurrent_payment_amount_extra = False

    def _inverse_recurrent_payment_amount_extra(self):
        for ptav in self:
            if ptav.has_recurrent_payment:
                pt = ptav.product_tmpl_id
                ptav.price_extra = (
                    ptav.recurrent_payment_amount_extra
                    * pt.list_price
                    / pt.recurrent_payment_amount
                )
