import datetime

from .common import DeviceAsAServiceTC, add_attributes_to_product, create_config


class WizardCrmLeadPickingTC(DeviceAsAServiceTC):
    def setUp(self):
        super().setUp()

        self.fp3_plus_service_tmpl = self._create_rental_product("fp3+").product_tmpl_id
        self.fp3_plus_storable_tmpl = self.storable_product.copy({"name": "fp3+"})
        self.usbc_cable = self.env["product.template"].create(
            {
                "name": "Test USB-C Cable",
                "type": "product",
                "tracking": "none",
            }
        )
        self.protective_screen = self.env["product.template"].create(
            {
                "name": "Protective Screen",
                "type": "product",
                "tracking": "none",
            }
        )
        self.location_untracked = self.env["stock.location"].create(
            {
                "name": "Test Module stock location",
                "usage": "internal",
                "partner_id": 1,
                "location_id": self.env.ref(
                    "commown_devices.stock_location_new_devices"
                ).id,
            }
        )
        self.adjust_stock_notracking(
            self.usbc_cable.product_variant_id, self.location_untracked
        )
        # We don't ajdust stock of protective screen because lack of stock case is
        # tested
        self.attribute_usbc = self.env["product.attribute"].create(
            {"name": "Send Cable ?", "type": "select", "create_variant": "always"}
        )
        self.attribute_color = self.env.ref("product.product_attribute_2")
        color_values = self.env["product.attribute.value"].search(
            [("attribute_id.id", "=", self.attribute_color.id)]
        )
        usbc_values = self.env["product.attribute.value"].create(
            [
                {"attribute_id": self.attribute_usbc.id, "name": "Yes"},
                {"attribute_id": self.attribute_usbc.id, "name": "No"},
            ]
        )
        add_attributes_to_product(
            self.fp3_plus_service_tmpl,
            self.attribute_color,
            color_values,
        )
        add_attributes_to_product(
            self.fp3_plus_storable_tmpl,
            self.attribute_color,
            color_values,
        )
        add_attributes_to_product(
            self.fp3_plus_service_tmpl,
            self.attribute_usbc,
            usbc_values,
        )
        self.fp3_plus_storable_tmpl.create_variant_ids()
        self.fp3_plus_service_tmpl.create_variant_ids()
        self.color1 = color_values[0]
        with_usbc = usbc_values.filtered(lambda v: v.name == "Yes")
        self.fp3_plus_storable_color1 = self.env["product.product"].search(
            [
                ("product_tmpl_id", "=", self.fp3_plus_storable_tmpl.id),
                ("attribute_value_ids.id", "ilike", self.color1.id),
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
        create_config(
            self.fp3_plus_service_tmpl,
            "secondary",
            self.usbc_cable,
            self.usbc_cable.product_variant_id,
            att_val_ids=with_usbc,
        )
        self.fp3_plus_service_color1_with_usb = self.env["product.product"].search(
            [
                ("product_tmpl_id", "=", self.fp3_plus_service_tmpl.id),
                ("attribute_value_ids", "ilike", self.color1.id),
                ("attribute_value_ids", "ilike", with_usbc.id),
            ]
        )
        self.so.order_line[0].product_id = self.fp3_plus_service_color1_with_usb
        self.adjust_stock(self.fp3_plus_storable_color1, serial="test-fp3+-1")
        self.adjust_stock(self.fp3_plus_storable_color1, serial="test-fp3+-2")
        self.fp3_plus_service_tmpl.onchange_storable_config_ids()

    def prepare_wizard(self, related_entity, relation_field, user_choices=None):
        wizard_name = "%s.picking.wizard" % related_entity._name
        return self.prepare_ui(
            wizard_name, related_entity, relation_field, user_choices=user_choices
        )

    def get_lead(self):
        return self.env["crm.lead"].search(
            [
                ("so_line_id", "=", self.so.order_line.ids[0]),
            ]
        )[0]

    def test_ui(self):

        lead = self.get_lead()

        # Get values to test
        defaults, possibilities = self.prepare_wizard(lead, "lead_id")

        # Check defaults

        self.assertEqual(defaults["lead_id"], lead.id)
        self.assertEqual(
            sorted(defaults["all_products"][0][2]),
            sorted(
                [
                    self.fp3_plus_storable_color1.id,
                    self.usbc_cable.product_variant_id.id,
                    self.protective_screen.product_variant_id.id,
                ]
            ),
        )

        # Check domains
        self.assertEqual(
            possibilities["lot_ids"].mapped("name"),
            ["test-fp3+-1", "test-fp3+-2"],
        )

    def test_picking(self):

        # Prepare test data
        lead = self.get_lead()

        defaults, possibilities = self.prepare_wizard(lead, "lead_id")

        date = datetime.datetime(2020, 1, 10, 16, 2, 34)
        wizard = (
            self.env["crm.lead.picking.wizard"]
            .with_context({"default_lead_id": lead.id})
            .create(
                {
                    "lead_id": lead.id,
                    "date": date,
                }
            )
        )
        lot = possibilities["lot_ids"][0]
        wizard.lot_ids = lot

        with self.assertRaises(Warning) as err:
            picking = wizard.create_picking()
        self.assertEqual(
            "Not enough %s in stock" % self.protective_screen.name,
            err.exception.args[0],
        )

        self.adjust_stock_notracking(
            self.protective_screen.product_variant_id, self.location_untracked
        )

        picking = wizard.create_picking()

        # Check the result
        loc_new = self.env.ref("commown_devices.stock_location_new_devices")

        self.assertIn(picking.id, lead.contract_id.picking_ids.ids)
        self.assertEqual(picking.state, "assigned")
        self.assertEqual(picking.move_type, "direct")
        self.assertEqual(picking.location_id, loc_new)

        move_lines = picking.move_line_ids
        self.assertEqual(len(move_lines), 3)
        loc_partner = self.so.partner_id.get_or_create_customer_location()
        self.assertEqual(
            sorted(move_lines.mapped("location_id").ids),
            sorted([self.location_fp3_new.id, self.location_untracked.id]),
        )
        self.assertEqual(move_lines.mapped("location_dest_id"), loc_partner)

        self.assertEqual(move_lines.mapped("lot_id.name"), [lot.name])
