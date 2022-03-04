from .common import DeviceAsAServiceTC


class WizardCrmLeadPickingTC(DeviceAsAServiceTC):

    def prepare_wizard(self, related_entity, relation_field, user_choices=None):
        wizard_name = "%s.picking.wizard" % related_entity._name
        return self.prepare_ui(wizard_name, related_entity, relation_field,
                               user_choices=user_choices)

    def get_lead(self):
        return self.env["crm.lead"].search([
            ("so_line_id", "=", self.so.order_line.ids[0]),
        ])[0]

    def test_ui(self):

        # Prepare test data
        lead = self.get_lead()
        fp3_plus = self.storable_product.copy({"name": "fp3+"})
        self.adjust_stock(serial="my-fp3-1")
        self.adjust_stock(serial="my-fp3-2")
        self.adjust_stock(serial="my-fp3-3")
        self.adjust_stock(fp3_plus.product_variant_id, serial="my-fp3+-1")
        self.adjust_stock(fp3_plus.product_variant_id, serial="my-fp3+-2")

        # Get values to test
        defaults, possibilities = self.prepare_wizard(lead, "lead_id")

        # Check defaults
        self.assertEqual(defaults["lead_id"], lead.id)
        self.assertEqual(defaults["product_tmpl_id"], self.storable_product.id)

        # Check domains
        self.assertEqual(sorted(possibilities["product_tmpl_id"]),
                         [self.storable_product, fp3_plus])
        self.assertEqual(possibilities["variant_id"],
                         self.storable_product.product_variant_id)
        self.assertEqual(sorted(possibilities["lot_id"].mapped("name")),
                         ["my-fp3-1", "my-fp3-2", "my-fp3-3"])

        # Check with another user product choice
        defaults, possibilities = self.prepare_wizard(
            lead, "lead_id", user_choices={"product_tmpl_id": fp3_plus.id})

        self.assertEqual(possibilities["variant_id"],
                         fp3_plus.product_variant_id)
        self.assertEqual(sorted(possibilities["lot_id"].mapped("name")),
                         ["my-fp3+-1", "my-fp3+-2"])

    def test_picking(self):

        # Prepare test data
        lead = self.get_lead()
        self.adjust_stock(serial="init-fp3")

        # Create the picking
        vals, possibilities = self.prepare_wizard(lead, "lead_id")

        for k, v in possibilities.items():
            vals.setdefault(k, v[0].id)
        wizard = self.env["crm.lead.picking.wizard"].create(vals)
        picking = wizard.create_picking()

        # Check the result
        self.assertIn(picking, lead.contract_id.picking_ids)
        self.assertEqual(picking.state, "assigned")
        self.assertEqual(picking.move_type, "direct")

        move_lines = picking.move_line_ids
        self.assertEqual(len(move_lines), 1)

        loc_new = self.env.ref("commown_devices.stock_location_new_devices")
        loc_partner = self.so.partner_id.get_or_create_customer_location()
        self.assertEqual(move_lines.location_id.location_id, loc_new)
        self.assertEqual(move_lines.location_dest_id, loc_partner)

        self.assertEqual(move_lines.lot_id.name, "init-fp3")
