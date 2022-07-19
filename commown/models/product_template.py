from odoo import models, fields


class SupportedProductTemplate(models.Model):
    """Add groups to products, where users who bought the product are
    automatically added.
    """

    _inherit = "product.template"

    support_group_ids = fields.Many2many(
        "res.groups", "supported_product_tmpl_ids", string="Support groups"
    )
