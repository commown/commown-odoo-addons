from odoo.exceptions import AccessError, UserError
from odoo.tests import Form, TransactionCase

from .common import NetinstallMixin


class NetinstallerFeatureTC(TransactionCase, NetinstallMixin):
    "Tests related to the netinstaller feature and feature value models"

    def test_perm_user(self):
        """Users must belong to the netinstaller user group to read netinstaller features
        and feature values.
        """

        user = self.env.ref("base.user_demo")
        f_user_model = self.env["commown_netinstaller.feature"].with_user(user)
        fv_user_model = self.env["commown_netinstaller.feature.value"].with_user(user)

        with self.assertRaises(AccessError):
            f_user_model.search_count([])

        with self.assertRaises(AccessError):
            fv_user_model.search_count([])

        user.groups_id |= self.lref("group_netinstaller_user")
        self.assertTrue(f_user_model.search_count([]))
        self.assertTrue(fv_user_model.search_count([]))

    def test_perm_manager(self):
        """Users must belong to the netinstaller manager group to modify
        netinstaller features and feature values.
        """
        user = self.env.ref("base.user_demo")
        user.groups_id |= self.lref("group_netinstaller_user")

        with self.assertRaises(AccessError):
            self.lref("ram").with_user(user).name = "dummy"

        with self.assertRaises(AccessError):
            self.lref("ram-8").with_user(user).value = 12

        user.groups_id |= self.lref("group_netinstaller_feature_manager")

        # Test update
        self.lref("ram").with_user(user).name = "dummy"
        self.assertEqual(self.lref("ram").name, "dummy")

        self.lref("ram-8").with_user(user).value = "12"
        self.assertEqual(self.lref("ram-8").value, "12")

        # Test remove
        self.lref("nv").with_user(user).unlink()
        self.lref("motherboard-model").with_user(user).unlink()

        # Test create
        feature = (
            self.env["commown_netinstaller.feature"]
            .with_user(user)
            .create(
                {"name": "myfeat", "converter": "str"},
            )
        )
        self.env["commown_netinstaller.feature.value"].with_user(user).create(
            {"value": "no-matter", "feature_id": feature.id},
        )

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
