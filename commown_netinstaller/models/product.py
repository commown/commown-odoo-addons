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


class Product(models.Model):
    _inherit = "product.product"

    cumulated_netinstaller_feature_value_ids = fields.One2many(
        "commown_netinstaller.feature.value",
        string="All netinstaller feature values applying to this product",
        compute="_compute_cumulated_netinstaller_feature_values",
    )

    def _compute_cumulated_netinstaller_feature_values(self):
        for rec in self:
            pp_values = rec.mapped(
                "product_template_attribute_value_ids.product_attribute_value_id"
            )
            attr_fvalues = self.env["commown_netinstaller.feature.value"].search(
                [("product_attribute_value_ids", "in", pp_values.ids)]
            )
            pt_fvalues = rec.product_tmpl_id.netinstaller_feature_value_ids.filtered(
                lambda v: v.feature_id not in attr_fvalues.mapped("feature_id")
            )
            rec.cumulated_netinstaller_feature_value_ids = attr_fvalues | pt_fvalues

    def netinstaller_feature_typed_values(self):
        self.ensure_one()
        return {
            fvalue.feature_id.name: fvalue.typed_value()
            for fvalue in self.cumulated_netinstaller_feature_value_ids
        }
