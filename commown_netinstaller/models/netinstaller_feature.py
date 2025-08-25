from odoo import api, fields, models


class NetinstallerFeature(models.Model):
    _name = "commown_netinstaller.feature"
    _description = "Describe an hardware/ software feature needed to prepare the device"
    _sql_constraints = [
        ("name_uniq", "unique (name)", "The feature name must be unique"),
    ]

    name = fields.Char(
        required=True,
    )

    feature_value_ids = fields.One2many(
        string="Feature values",
        comodel_name="commown_netinstaller.feature.value",
        inverse_name="feature_id",
    )

    product_attribute_ids = fields.Many2many(
        "product.attribute",
        string="Product attributes",
        relation="product_attribute_netinstaller_features",
        column1="attribute_id",
        column2="feature_id",
    )

    @api.onchange("product_attribute_ids")
    def onchange_product_attribute_ids(self):
        product_attrs = self.product_attribute_ids

        for value in self.feature_value_ids:
            value.product_attribute_value_ids = (
                value.product_attribute_value_ids.filtered(
                    lambda p_attr_val: p_attr_val.attribute_id in product_attrs
                )
            )
