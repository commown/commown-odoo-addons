from odoo import fields, models


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
