from .common import DeviceAsAServiceTC, add_attributes_to_product, create_config


class ProductTemplateTC(DeviceAsAServiceTC):
    def setUp(self, *args, **kwargs):
        super(ProductTemplateTC, self).setUp(*args, **kwargs)

        self.fp3_plus_service_tmpl = self._create_rental_product("fp3+").product_tmpl_id
        self.fp3_plus_storable_tmpl = self.storable_product.copy({"name": "fp3+"})

        self.protective_screen = self.env["product.template"].create(
            {
                "name": "Protective Screen",
                "type": "product",
                "tracking": "none",
            }
        )

        self.attribute_color = self.env.ref("product.product_attribute_2")
        color_values = self.env["product.attribute.value"].search(
            [("attribute_id.id", "=", self.attribute_color.id)]
        )

        add_attributes_to_product(
            self.fp3_plus_storable_tmpl,
            self.attribute_color,
            color_values,
        )
        self.fp3_plus_storable_tmpl.create_variant_ids()

        self.color1 = color_values[0]
        self.color2 = color_values[1]
        self.fp3_plus_storable_color1 = self.env["product.product"].search(
            [
                ("product_tmpl_id", "=", self.fp3_plus_storable_tmpl.id),
                ("attribute_value_ids.id", "ilike", self.color1.id),
            ]
        )
        self.fp3_plus_storable_color2 = self.env["product.product"].search(
            [
                ("product_tmpl_id", "=", self.fp3_plus_storable_tmpl.id),
                ("attribute_value_ids.id", "ilike", self.color2.id),
            ]
        )

        create_config(
            self.fp3_plus_service_tmpl,
            "primary",
            self.fp3_plus_storable_tmpl,
            self.fp3_plus_storable_color1,
            att_val_ids=self.color1,
        )

        create_config(
            self.fp3_plus_service_tmpl,
            "secondary",
            self.protective_screen,
            self.protective_screen.product_variant_id,
        )

    def test_behavior_on_new_variant_or_config(self):
        self.assertEqual(
            len(
                self.fp3_plus_service_tmpl.mapped(
                    "product_variant_ids.primary_storable_variant_id"
                )
            ),
            0,
        )
        self.assertEqual(
            len(
                self.fp3_plus_service_tmpl.mapped(
                    "product_variant_ids.secondary_storable_variant_ids"
                )
            ),
            0,
        )
        add_attributes_to_product(
            self.fp3_plus_service_tmpl,
            self.attribute_color,
            self.color1 + self.color2,
        )
        self.fp3_plus_service_tmpl.create_variant_ids()
        # Check that primary and secondary variant has been affected to fp3+ of color1
        fp3_plus_service_color1 = self.env["product.product"].search(
            [
                ("product_tmpl_id", "=", self.fp3_plus_service_tmpl.id),
                ("attribute_value_ids.id", "ilike", self.color1.id),
            ]
        )
        self.assertEqual(
            fp3_plus_service_color1.primary_storable_variant_id,
            self.fp3_plus_storable_color1,
        )
        self.assertEqual(
            fp3_plus_service_color1.secondary_storable_variant_ids,
            self.protective_screen.product_variant_id,
        )

        # Create primary variant config to fp3 plus color2
        create_config(
            self.fp3_plus_service_tmpl,
            "primary",
            self.fp3_plus_storable_tmpl,
            self.fp3_plus_storable_color2,
            att_val_ids=self.color2,
        )
        # Manualy set _origin to emulate onchange methode
        self.fp3_plus_service_tmpl._origin = self.fp3_plus_service_tmpl
        # Manually trigger onchange method
        self.fp3_plus_service_tmpl.onchange_storable_config_ids()
        # Check primary variant has been set
        fp3_plus_service_color2 = self.env["product.product"].search(
            [
                ("product_tmpl_id", "=", self.fp3_plus_service_tmpl.id),
                ("attribute_value_ids.id", "ilike", self.color2.id),
            ]
        )
        self.assertEqual(
            fp3_plus_service_color2.primary_storable_variant_id,
            self.fp3_plus_storable_color2,
        )
        self.assertEqual(
            fp3_plus_service_color2.secondary_storable_variant_ids,
            self.protective_screen.product_variant_id,
        )

        # Check that it is impossible to have more than one primary variant associted to one service
        with self.assertRaises(AssertionError) as err:
            false_config = create_config(
                self.fp3_plus_service_tmpl,
                "primary",
                self.fp3_plus_storable_tmpl,
                self.fp3_plus_storable_color1,
                att_val_ids=self.color2,
            )
            self.fp3_plus_service_tmpl.onchange_storable_config_ids()
        self.assertEqual(
            (
                "More than one primary variant configured for %s with attributes %s"
                % (
                    fp3_plus_service_color2.name,
                    fp3_plus_service_color2.attribute_value_ids.mapped("name"),
                )
            ),
            err.exception.args[0],
        )
        # Manually remove false config
        false_config.unlink()

        # Check that a warning is isued if two secondary variants have the same template
        backcover = self.env["product.template"].create(
            {
                "name": "Back Cover",
                "type": "product",
                "tracking": "none",
            }
        )
        add_attributes_to_product(
            backcover,
            self.attribute_color,
            self.color1 + self.color2,
        )
        backcover.create_variant_ids()
        back_cover_color1 = self.env["product.product"].search(
            [
                ("product_tmpl_id", "=", backcover.id),
                ("attribute_value_ids.id", "ilike", self.color1.id),
            ]
        )
        back_cover_color2 = self.env["product.product"].search(
            [
                ("product_tmpl_id", "=", backcover.id),
                ("attribute_value_ids.id", "ilike", self.color2.id),
            ]
        )
        # Manualy set _origin to emulate onchange methode
        self.fp3_plus_service_tmpl._origin = self.fp3_plus_service_tmpl
        create_config(
            self.fp3_plus_service_tmpl,
            "secondary",
            backcover,
            back_cover_color1,
            att_val_ids=self.color1,
        )
        self.fp3_plus_service_tmpl.onchange_storable_config_ids()
        with self.assertRaises(Warning) as err2:
            # Manualy set _origin to emulate onchange methode
            self.fp3_plus_service_tmpl._origin = self.fp3_plus_service_tmpl
            create_config(
                self.fp3_plus_service_tmpl,
                "secondary",
                backcover,
                back_cover_color2,
                att_val_ids=self.color1,
            )
            self.fp3_plus_service_tmpl.onchange_storable_config_ids()
        self.assertEqual(
            (
                "For product %s, two secondary variants derive from the same template,"
                " are you sure that there is no configuration mistake ?"
                % fp3_plus_service_color2.name
            ),
            err2.exception.args[0],
        )
