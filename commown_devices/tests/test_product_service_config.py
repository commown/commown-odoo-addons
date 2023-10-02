from .common import DeviceAsAServiceTC, add_attributes_to_product, create_config


class ProductServiceConfigTC(DeviceAsAServiceTC):
    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)

        self.attribute_color = self.env.ref("product.product_attribute_2")
        color_values = self.env["product.attribute.value"].search(
            [("attribute_id", "=", self.attribute_color.id)]
        )
        self.color1 = color_values[0]
        self.color2 = color_values[1]

        self.fp3_service_tmpl = self._create_rental_product("fp3+").product_tmpl_id

        self.protective_screen = self.env["product.template"].create(
            {
                "name": "Protective Screen",
                "type": "product",
                "tracking": "none",
            }
        )

        add_attributes_to_product(
            self.fp3_service_tmpl,
            self.attribute_color,
            self.color1 + self.color2,
        )
        self.fp3_service_tmpl.create_variant_ids()

        self.fp3_service_color1 = self.env["product.product"].search(
            [
                ("product_tmpl_id", "=", self.fp3_service_tmpl.id),
                ("attribute_value_ids", "=", self.color1.id),
            ]
        )
        self.fp3_service_color2 = self.env["product.product"].search(
            [
                ("product_tmpl_id", "=", self.fp3_service_tmpl.id),
                ("attribute_value_ids", "=", self.color2.id),
            ]
        )

    def test_crud(self):
        # Check prerequisite
        self.assertFalse(self.fp3_service_color2.secondary_storable_variant_ids)

        # Check create
        c = create_config(
            self.fp3_service_tmpl,
            "secondary",
            self.protective_screen,
            self.protective_screen.product_variant_id,
        )

        self.assertEqual(
            self.fp3_service_color2.secondary_storable_variant_ids,
            self.protective_screen.product_variant_id,
        )

        # Check update
        c.attribute_value_ids |= self.color1

        self.assertFalse(self.fp3_service_color2.secondary_storable_variant_ids)

        self.assertEqual(
            self.fp3_service_color1.secondary_storable_variant_ids,
            self.protective_screen.product_variant_id,
        )

        # Check unlink
        c.unlink()
        self.assertFalse(self.fp3_service_color1.secondary_storable_variant_ids)
        self.assertFalse(self.fp3_service_color2.secondary_storable_variant_ids)
