from odoo import fields, models


class SupportedProductTemplate(models.Model):
    """Add groups to products, where users who bought the product are
    automatically added.
    """

    _inherit = "product.template"

    support_group_ids = fields.Many2many(
        "res.groups", "supported_product_tmpl_ids", string="Support groups"
    )

    sale_line_warn_msg = fields.Text(translate=True)
