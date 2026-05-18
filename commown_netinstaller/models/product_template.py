from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    netinstaller_feature_value_ids = fields.Many2many(
        string="Netinstaller feature values",
        comodel_name="commown_netinstaller.feature.value",
        relation="product_template_netinstaller_feature_values",
        column1="product_template_id",
        column2="feature_value_id",
    )
