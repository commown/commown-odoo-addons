from odoo import _, api, fields, models
from odoo.exceptions import UserError


class NetInstallerFeatureValue(models.Model):
    _name = "commown_netinstaller.feature.value"
    _description = "Represents a possible value of a netinstaller feature"
    _order = "feature_id, value"
    _rec_names_search = ["feature_id", "value"]
    _sql_constraints = [
        (
            "feature_value_uniq",
            "unique(value, feature_id)",
            "Identical values for a given feature",
        )
    ]

    value = fields.Char(required=True)

    feature_id = fields.Many2one("commown_netinstaller.feature", required=True)

    product_attribute_value_ids = fields.Many2many(
        string="Product attribute values",
        comodel_name="product.attribute.value",
        relation="product_attribute_value_netinstaller_feature_values",
        column1="attribute_value_id",
        column2="feature_value_id",
    )

    product_attr_val_domain = fields.Binary(compute="_compute_product_attr_val_domain")

    def name_get(self):
        result = []
        for record in self:
            name = "%s = %s" % (record.feature_id.name, record.value)
            result.append((record.id, name))
        return result

    def typed_value(self):
        self.ensure_one()
        return self.feature_id.typed_value(self.value)

    @api.constrains("value")
    def _check_value_compatible_with_converter(self):
        for value in self:
            try:
                value.typed_value()
            except ValueError as exc:
                raise UserError(
                    _(
                        "This value is incompatible with the current convertion method ('%s')",
                        value.feature_id.converter,
                    )
                ) from exc

    @api.depends("feature_id.product_attribute_ids")
    def _compute_product_attr_val_domain(self):
        for val in self:
            attributes = val.feature_id.product_attribute_ids
            val.product_attr_val_domain = [("attribute_id", "in", attributes.ids)]
