from odoo import fields, models


class Product(models.Model):
    _inherit = "product.product"

    cumulated_netinstaller_feature_value_ids = fields.One2many(
        "commown_netinstaller.feature.value",
        string="All netinstaller feature values",
        compute="_compute_cumulated_netinstaller_feature_values",
        store=False,
    )

    def _compute_cumulated_netinstaller_feature_values(self):
        for record in self:
            pp_values = record.mapped(
                "product_template_attribute_value_ids.product_attribute_value_id"
            )
            attr_fvalues = self.env["commown_netinstaller.feature.value"].search(
                [("product_attribute_value_ids", "in", pp_values.ids)]
            )
            pt_fvalues = record.product_tmpl_id.netinstaller_feature_value_ids.filtered(
                lambda v: v.feature_id not in attr_fvalues.mapped("feature_id")
            )
            record.cumulated_netinstaller_feature_value_ids = attr_fvalues | pt_fvalues
