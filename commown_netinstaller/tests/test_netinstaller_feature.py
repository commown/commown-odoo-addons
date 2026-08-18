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
