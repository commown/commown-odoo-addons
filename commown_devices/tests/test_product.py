from odoo.exceptions import UserError

from .common import DeviceAsAServiceTC, add_attributes_to_product, create_config


class ProductServiceStorableConfigTC(DeviceAsAServiceTC):
    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)

        self.attribute_color = self.env.ref("product.product_attribute_2")
        color_values = self.env["product.attribute.value"].search(
            [("attribute_id", "=", self.attribute_color.id)]
        )
        self.color1 = color_values[0]
        self.color2 = color_values[1]

        self.fp3_service_tmpl = self._create_rental_product("fp3+").product_tmpl_id
        self.fp3_storable_tmpl = self.storable_product.copy({"name": "fp3+"})

        self.protective_screen = self.env["product.template"].create(
            {
                "name": "Protective Screen",
                "type": "product",
                "tracking": "none",
            }
        )

        self.backcover = self.env["product.template"].create(
            {
                "name": "Back Cover",
                "type": "product",
                "tracking": "none",
            }
        )
        add_attributes_to_product(
            self.backcover,
            self.attribute_color,
            self.color1 + self.color2,
        )
        self.backcover.create_variant_ids()
        self.backcover1, self.backcover2 = self.backcover.product_variant_ids

        add_attributes_to_product(
            self.fp3_storable_tmpl,
            self.attribute_color,
            color_values,
        )
        self.fp3_storable_tmpl.create_variant_ids()

        add_attributes_to_product(
            self.fp3_service_tmpl,
            self.attribute_color,
            self.color1 + self.color2,
        )
        self.fp3_service_tmpl.create_variant_ids()

        self.fp3_storable_color1 = self.env["product.product"].search(
            [
                ("product_tmpl_id", "=", self.fp3_storable_tmpl.id),
                ("attribute_value_ids.id", "ilike", self.color1.id),
            ]
        )
        self.fp3_storable_color2 = self.env["product.product"].search(
            [
                ("product_tmpl_id", "=", self.fp3_storable_tmpl.id),
                ("attribute_value_ids.id", "ilike", self.color2.id),
            ]
        )
        self.fp3_service_color2 = self.env["product.product"].search(
            [
                ("product_tmpl_id", "=", self.fp3_service_tmpl.id),
                ("attribute_value_ids.id", "ilike", self.color2.id),
            ]
        )

    def test_behavior_on_new_variant(self):
        """Check that primary and secondary storable variants are set when a new
        variant is created"""
        new_attr = self.env.ref("product_rental.attr_cpu")
        create_config(
            self.fp3_service_tmpl,
            "primary",
            self.fp3_storable_tmpl,
            self.fp3_storable_color1,
            att_val_ids=new_attr.value_ids[0],
        )

        create_config(
            self.fp3_service_tmpl,
            "secondary",
            self.protective_screen,
            self.protective_screen.product_variant_id,
        )

        add_attributes_to_product(
            self.fp3_service_tmpl,
            new_attr,
            new_attr.value_ids,
        )
        self.fp3_service_tmpl.create_variant_ids()

        new_var = self.env["product.product"].search(
            [
                ("product_tmpl_id", "=", self.fp3_service_tmpl.id),
                ("attribute_value_ids", "ilike", new_attr.value_ids[0].id),
            ],
            limit=1,
        )

        self.assertEqual(
            new_var.primary_storable_variant_id,
            self.fp3_storable_color1,
        )
        self.assertEqual(
            new_var.secondary_storable_variant_ids,
            self.protective_screen.product_variant_id,
        )

    def test_behavior_on_new_config(self):
        """Check that primary and secondary storable variants are set when a new
        config is created"""
        self.assertFalse(
            self.fp3_service_tmpl.mapped(
                "product_variant_ids.primary_storable_variant_id"
            )
        )
        self.assertFalse(
            self.fp3_service_tmpl.mapped(
                "product_variant_ids.secondary_storable_variant_ids"
            )
        )

        create_config(
            self.fp3_service_tmpl,
            "primary",
            self.fp3_storable_tmpl,
            self.fp3_storable_color1,
            att_val_ids=self.color1,
        )

        create_config(
            self.fp3_service_tmpl,
            "secondary",
            self.protective_screen,
            self.protective_screen.product_variant_id,
        )
        # Check that primary and secondary variants have been affected to fp3+ of color1
        fp3_service_color1 = self.env["product.product"].search(
            [
                ("product_tmpl_id", "=", self.fp3_service_tmpl.id),
                ("attribute_value_ids.id", "ilike", self.color1.id),
            ]
        )
        self.assertEqual(
            fp3_service_color1.primary_storable_variant_id,
            self.fp3_storable_color1,
        )
        self.assertEqual(
            fp3_service_color1.secondary_storable_variant_ids,
            self.protective_screen.product_variant_id,
        )

    def test_error_on_multiple_primary_config(self):
        """Check that it is impossible to have more than one primary variant associted
        to one service"""
        create_config(
            self.fp3_service_tmpl,
            "primary",
            self.fp3_storable_tmpl,
            self.fp3_storable_color2,
            att_val_ids=self.color2,
        )
        with self.assertRaises(UserError) as err:
            false_config = create_config(
                self.fp3_service_tmpl,
                "primary",
                self.fp3_storable_tmpl,
                self.fp3_storable_color1,
                att_val_ids=self.color2,
            )
        self.assertEqual(
            (
                "More than one primary variant configured for %s with attributes %s"
                % (
                    self.fp3_service_color2.name,
                    self.fp3_service_color2.attribute_value_ids.mapped("name"),
                )
            ),
            err.exception.name,
        )

    def test_error_on_multiple_secondary_config(self):
        """Check that a warning is issued if two secondary variants have the same template"""

        create_config(
            self.fp3_service_tmpl,
            "secondary",
            self.backcover,
            self.backcover1,
            att_val_ids=self.color1,
        )
        with self.assertRaises(UserError) as err2:
            create_config(
                self.fp3_service_tmpl,
                "secondary",
                self.backcover,
                self.backcover2,
                att_val_ids=self.color1,
            )
        self.assertEqual(
            (
                "For product %s, two secondary variants derive from the same template,"
                " are you sure that there is no configuration mistake ?"
                % self.fp3_service_color2.name
            ),
            err2.exception.name,
        )
