from odoo import fields, models


class Product(models.Model):
    _inherit = "product.template"

    storable_product_id = fields.Many2one(
        "product.template",
        string="Storable product",
        domain='[("type", "=", "product")]',
    )

    storable_config_ids = fields.One2many(
        string="Storable configurations",
        comodel_name="product.service_storable_config",
        inverse_name="service_tmpl_id",
    )
