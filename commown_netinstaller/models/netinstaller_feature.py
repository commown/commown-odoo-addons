from odoo import _, api, fields, models
from odoo.exceptions import UserError


class NetinstallerFeature(models.Model):
    _name = "commown_netinstaller.feature"
    _description = "Describe an hardware/ software feature needed to prepare the device"
    _order = "name"
    _sql_constraints = [
        ("name_uniq", "unique (name)", "The feature name must be unique"),
    ]

    _CONVERTERS = {"str": str, "int": int}

    name = fields.Char(
        required=True,
    )

    converter = fields.Selection(
        [("str", "String"), ("int", "Integer")],
        default="str",
        required=True,
        help=(
            "Name of the function to convert a string representation"
            " of a value of this feature into a typed value"
        ),
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

    def typed_value(self, value):
        self.ensure_one()
        return self._CONVERTERS[self.converter](value)

    @api.constrains("converter")
    def _check_converter_compatible_with_values(self):
        "Any assigned converter should be compatible with current values"
        for feature in self:
            incompatible_values = []
            for feat_value in feature.feature_value_ids:
                try:
                    feat_value.typed_value()
                except ValueError:
                    incompatible_values.append(feat_value.value)
            if incompatible_values:
                raise UserError(
                    _(
                        "The new converter method is incompatible with the following values: '%s'",
                        "', '".join(incompatible_values),
                    )
                )

    @api.onchange("product_attribute_ids")
    def onchange_product_attribute_ids(self):
        for feat in self:
            product_attrs = feat.product_attribute_ids._origin

            for value in feat.feature_value_ids:
                value.product_attribute_value_ids = (
                    value.product_attribute_value_ids.filtered(
                        lambda p_attr_val: p_attr_val.attribute_id in product_attrs
                    )
                )
