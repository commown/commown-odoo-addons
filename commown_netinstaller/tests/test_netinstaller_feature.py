from odoo.exceptions import UserError
from odoo.tests import TransactionCase

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
