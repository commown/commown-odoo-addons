import six

from .common import DeviceAsAServiceTC


class WizardProjectIssuePickingTC(DeviceAsAServiceTC):

    def setUp(self):
        super(WizardProjectIssuePickingTC, self).setUp()
        self.assertTrue(self.so.partner_id.get_or_create_customer_location())

        lot = self.adjust_stock(serial=u"init-fp3")
        self.send_device(u"init-fp3", date="2000-01-02")

        self.issue = self.env["project.issue"].create({
            "name": u"Test issue",
            "contract_id": self.so.order_line.contract_id.id,
            "partner_id": self.so.partner_id.id,
            "lot_id": lot.id,
        })

    def send_device(self, serial, contract=None, date=None):
        contract = contract or self.so.order_line.contract_id
        quant = self.env["stock.quant"].search([("lot_id.name", "=", serial)])
        contract.send_device(quant, date, True)

    def prepare_wizard(self, direction, issue=None, user_choices=None):
        issue = issue or self.issue
        _name = "project.issue.%s.picking.wizard" % direction
        wizard_model = self.env[_name].with_context({
            "default_issue_id": issue.id,
            "active_model": issue._name,
            "active_id": issue.id,
            "active_ids": issue.ids,
        })
        # Get default values
        fields = wizard_model.fields_get()
        defaults = wizard_model.default_get(fields.keys())
        choices = defaults.copy()
        if user_choices is None:
            user_choices = {}
        choices.update(user_choices)
        # Execute onchange methods
        domains = {name: field.get("domain", None)
                   for name, field in fields.items()}
        specs = wizard_model._onchange_spec()
        result = wizard_model.onchange(
            choices, user_choices.keys(), specs)
        updates = result.get("value", {})
        for name, val in updates.iteritems():
            if isinstance(val, tuple):
                updates[name] = val[0]
        choices.update(updates)
        # Apply domain restrictions
        for name, domain in result.get("domain", {}).iteritems():
            domains[name] = domain
        possible_values = {}
        for name, field in fields.items():
            domain = domains[name]
            if domain is None:
                continue
            if isinstance(domain, six.string_types):
                domain = eval(domain, choices.copy())
            possible_values[name] = self.env[field["relation"]].search(domain)
        return defaults, possible_values

    def test_outward_ui(self):

        loc_new = self.location_fp3_new
        loc_rep = loc_new.copy({"name": u"Repackaged FP3 devices"})

        self.adjust_stock(serial=u"my-fp3-1", location=loc_new)
        self.adjust_stock(serial=u"my-fp3-2", location=loc_new)
        self.adjust_stock(serial=u"my-fp3-3", location=loc_rep)

        product2 = self.storable_product.copy()
        self.adjust_stock(serial=u"my-p2-1", location=loc_new,
                          product=product2.product_variant_id)
        self.adjust_stock(serial=u"my-p2-2", location=loc_new,
                          product=product2.product_variant_id)

        defaults, possibilities = self.prepare_wizard("outward")

        # Check defaults of issue_id, date, product_tmpl_id, variant_id
        self.assertEqual(defaults["issue_id"], self.issue.id)
        self.assertEqual(defaults["product_tmpl_id"],
                         self.issue.lot_id.product_id.product_tmpl_id.id)
        self.assertEqual(defaults["variant_id"],
                         self.issue.lot_id.product_id.id)

        # Check domains of location_id, product_id, quant_id
        self.assertEqual(sorted(possibilities["product_tmpl_id"]),
                         [self.storable_product, product2])
        self.assertEqual(possibilities["variant_id"],
                         self.storable_product.product_variant_id)
        self.assertEqual(sorted(possibilities["lot_id"].mapped("name")),
                         [u"my-fp3-1", u"my-fp3-2", u"my-fp3-3"])

        # Check with another user choice for location_id
        defaults, possibilities = self.prepare_wizard(
            "outward", user_choices={"product_tmpl_id": product2.id})

        self.assertEqual(possibilities["variant_id"],
                         product2.product_variant_id)
        self.assertEqual(sorted(possibilities["lot_id"].mapped("name")),
                         [u"my-p2-1", u"my-p2-2"])

    def test_outward_picking(self):
        # Test setup
        loc_new = self.location_fp3_new
        self.adjust_stock(serial=u"my-fp3", location=loc_new)

        # Create the wizard and the picking
        vals, possibilities = self.prepare_wizard("outward")
        for k, v in possibilities.items():
            vals.setdefault(k, v[0].id)
        wizard = self.env["project.issue.outward.picking.wizard"].create(vals)
        picking = wizard.create_picking()

        # Check resulting picking
        self.assertIn(picking, self.issue.contract_id.picking_ids)
        self.assertEqual(picking.state, u"assigned")
        self.assertEqual(picking.move_type, u"direct")

        partner = self.issue.partner_id
        move = picking.move_lines
        self.assertEqual(len(move), 1)
        self.assertEqual(move.location_id, loc_new)
        self.assertEqual(move.location_dest_id,
                         partner.get_or_create_customer_location())
        self.assertEqual(picking.move_lines.mapped("lot_ids.name"), [u"my-fp3"])

    def test_inward_ui(self):
        # Test setup: 2 devices at the customer's location, 1 somewhere else
        loc_new = self.location_fp3_new
        self.adjust_stock(serial=u"my-fp3-1", location=loc_new)
        self.send_device(u"my-fp3-1")
        self.adjust_stock(serial=u"my-fp3-2", location=loc_new)
        self.send_device(u"my-fp3-2")
        self.adjust_stock(serial=u"my-fp3-3", location=loc_new)

        defaults, possibilities = self.prepare_wizard("inward")

        # Check defaults and domains
        self.assertEqual(defaults["issue_id"], self.issue.id)
        self.assertEqual(
            sorted(possibilities["lot_id"].mapped("name")),
            [u"init-fp3", u"my-fp3-1", u"my-fp3-2"])

    def test_inward_picking(self):
        # Create the wizard and the picking
        vals, possibilities = self.prepare_wizard("inward")
        for k, v in possibilities.items():
            vals.setdefault(k, v[0].id)
        wizard = self.env["project.issue.inward.picking.wizard"].create(vals)
        picking = wizard.create_picking()

        # Check resulting picking
        self.assertIn(picking, self.issue.contract_id.picking_ids)
        self.assertEqual(picking.state, u"assigned")
        self.assertEqual(picking.move_type, u"direct")

        loc_check = self.env.ref(
            "commown_devices.stock_location_devices_to_check")
        move = picking.move_lines
        self.assertEqual(len(move), 1)
        self.assertEqual(move.location_id,
                         self.so.partner_id.get_or_create_customer_location())
        self.assertEqual(move.location_dest_id, loc_check)
        self.assertEqual(picking.move_lines.mapped("lot_ids.name"),
                         [u"init-fp3"])
