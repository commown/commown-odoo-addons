from odoo import models, fields


class Product(models.Model):
    _inherit = "product.template"

    storable_product_id = fields.Many2one(
        'product.template',
        string='Storable product',
        domain='[("type", "=", "product")]',
    )
