from odoo import models, fields


class Product(models.Model):
    _inherit = "product.template"

    stockable_product_id = fields.Many2one(
        'product.product',
        string=u'Stockable product',
        domain='[("type", "=", "product")]',
    )
