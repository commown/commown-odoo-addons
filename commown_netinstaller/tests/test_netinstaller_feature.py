from odoo.exceptions import UserError
from odoo.tests import Form, TransactionCase

from .common import NetinstallMixin


class NetinstallerFeatureTC(TransactionCase, NetinstallMixin):
    def test_feature_value_display_name(self):
        "A feature value's display name should show its feature name and its value"
        self.assertEqual(self.lref("ram-8").display_name, "RAM = 8")
        self.assertEqual(self.lref("nv").display_name, "MODEL = NV4XMB,ME,MZ")

    def test_feature_value_typed(self):
        "A feature value should be converted to its target value type"
        feature = self.lref("ram")
        feature_value = self.lref("ram-8")

        feature.converter = "str"
        self.assertEqual(feature_value.typed_value(), "8")

        feature.converter = "int"
        self.assertEqual(feature_value.typed_value(), 8)

    def test_feature_value_incompatible_with_converter(self):
        "It shouldn't be possible to assign a value incompatible with a converter"
        with self.assertRaises(UserError) as exc:
            self.lref("ram-8").value = "error"
        self.assertIn("current convertion method ('int')", exc.exception.args[0])

    def test_feature_converter_incompatible_with_current_values(self):
        "A feature's convertion method cannot be changed if current values are incompatible"
        with self.assertRaises(UserError) as exc:
            self.lref("motherboard-model").converter = "int"
        self.assertIn(
            f"following values: '{self.lref('nv').value}'", exc.exception.args[0]
        )

    def test_feature_values_view_domain(self):
        feature = self.lref("ram")
        feature_value = self.lref("ram-8")

        feature.product_attribute_ids = False
        self.assertEqual(
            feature_value.product_attr_val_domain, [("attribute_id", "in", [])]
        )

        feature.product_attribute_ids |= self.lref("memory")
        feature_value.invalidate_recordset()
        self.assertEqual(
            feature_value.product_attr_val_domain,
            [("attribute_id", "in", [self.lref("memory").id])],
        )

    def test_feature_product_attributes_onchange(self):
        """
        After modifying the product attributes of a feature, its values should only have attribute values
        related to the new attributes
        """
        feature = self.lref("ram")
        ram_fval_8 = self.lref("ram-8")
        ram_fval_16 = self.lref("ram-16")

        ram_attribute_1 = self.lref("memory")
        ram_8_attrval_1 = self.lref("memory-8go")
        ram_16_attrval_1 = self.lref("memory-16go")

        ram_attribute_2 = ram_attribute_1.copy({"name": "Memory (Dummy)"})
        ram_8_attrval_2 = ram_attribute_2.value_ids.filtered(
            lambda val: val.name == "8 Go"
        )
        ram_16_attrval_2 = ram_attribute_2.value_ids.filtered(
            lambda val: val.name == "16 Go"
        )

        feature.product_attribute_ids |= ram_attribute_2
        ram_fval_8.product_attribute_value_ids |= ram_8_attrval_2
        ram_fval_16.product_attribute_value_ids |= ram_16_attrval_2

        self.assertEqual(
            ram_fval_8.product_attribute_value_ids,
            (ram_8_attrval_1 | ram_8_attrval_2),
        )
        self.assertEqual(
            ram_fval_16.product_attribute_value_ids,
            (ram_16_attrval_1 | ram_16_attrval_2),
        )

        with Form(feature) as feature_form:
            feature_form.product_attribute_ids.remove(id=ram_attribute_2.id)

        self.assertEqual(ram_fval_8.product_attribute_value_ids, ram_8_attrval_1)
        self.assertEqual(ram_fval_16.product_attribute_value_ids, ram_16_attrval_1)
