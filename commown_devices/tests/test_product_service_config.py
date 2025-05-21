from .common import DeviceAsAServiceTC, add_attributes_to_product, create_config


class ProductServiceConfigTC(DeviceAsAServiceTC):
    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)

        cls.attribute_color = cls.env.ref("product.product_attribute_2")
        cls.color1, cls.color2 = cls.attribute_color.value_ids[:2]

        cls.fp3_service_tmpl = cls._create_rental_product("fp3+").product_tmpl_id

        cls.protective_screen = cls.env["product.template"].create(
            {
                "name": "Protective Screen",
                "type": "product",
                "tracking": "none",
            }
        )

        add_attributes_to_product(
            cls.fp3_service_tmpl,
            cls.attribute_color,
            cls.color1 + cls.color2,
        )

        cls.fp3_service_color1 = cls.env["product.product"].search(
            [
                ("product_tmpl_id", "=", cls.fp3_service_tmpl.id),
                (
                    "product_template_variant_value_ids.product_attribute_value_id",
                    "=",
                    cls.color1.id,
                ),
            ]
        )
        cls.fp3_service_color2 = cls.env["product.product"].search(
            [
                ("product_tmpl_id", "=", cls.fp3_service_tmpl.id),
                (
                    "product_template_variant_value_ids.product_attribute_value_id",
                    "=",
                    cls.color2.id,
                ),
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
