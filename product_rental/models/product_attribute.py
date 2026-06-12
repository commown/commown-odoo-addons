from odoo import fields, models


class ProductTemplateAttributeValue(models.Model):
    _inherit = "product.template.attribute.value"

    has_recurrent_payment = fields.Boolean(
        "Is used by a product with a recurrent payment",
        related="product_tmpl_id.has_recurrent_payment",
    )

    recurrent_payment_amount_extra = fields.Float(
        string="Extra rental price",
        help="Extra price of the product rent for current variant",
        digits="Product Price",
        compute="_compute_recurrent_payment_amount_extra",
        inverse="_inverse_recurrent_payment_amount_extra",
    )

    def _compute_recurrent_payment_amount_extra(self):
        for ptav in self:
            ratio = ptav.product_tmpl_id.recurrent_payment_amount_ratio()
            if ratio is not None:
                ptav.recurrent_payment_amount_extra = ptav.price_extra / ratio
            else:
                ptav.recurrent_payment_amount_extra = False

    def _inverse_recurrent_payment_amount_extra(self):
        for ptav in self:
            ratio = ptav.product_tmpl_id.recurrent_payment_amount_ratio()
            if ratio is not None:
                ptav.price_extra = ptav.recurrent_payment_amount_extra * ratio
