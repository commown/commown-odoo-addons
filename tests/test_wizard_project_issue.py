import six

from odoo import fields

from .common import DeviceAsAServiceTC


class WizardProjectIssuePickingTC(DeviceAsAServiceTC):

    def setUp(self):
        super(WizardProjectIssuePickingTC, self).setUp()
        self.assertTrue(self.so.partner_id.set_customer_location())
        self.issue = self.env["project.issue"].create({
            "name": u"Test issue",
            "contract_id": self.so.order_line.contract_id.id,
            "partner_id": self.so.partner_id.id,
        })

    def prepare_wizard(self, direction, issue=None, user_choices=None):
        issue = issue or self.issue
        _name = "project.issue.%s.picking.wizard" % direction
        wizard_model = self.env[_name].with_context({
            "default_issue_id": issue.id,
            "active_model": issue._name,
            "active_id": issue.id,
            "active_ids": issue.ids,
        })
        fields = wizard_model.fields_get()
        defaults = wizard_model.default_get(fields.keys())
        possible_values = {}
        choices = defaults.copy()
        if user_choices is not None:
            choices.update(user_choices)
        for name, field in fields.items():
            if field.get("domain", None):
                domain = field["domain"]
                if isinstance(domain, six.string_types):
                    domain = eval(domain, choices.copy())
                possible_values[name] = self.env[field["relation"]].search(
                    domain)
        return defaults, possible_values

    def assertDatetimeAlmostEqual(self, d1, d2, seconds=2):
        _d1 = fields.Datetime.from_string(d1)
        _d2 = fields.Datetime.from_string(d2)
        self.assertTrue((_d2 - _d1).total_seconds() < seconds)

    def test_outward_defaults_and_domains(self):
        loc_new = self.env.ref("commown_devices.stock_location_fp3_new")
        loc_rep = self.env.ref("commown_devices.stock_location_fp3_repackaged")
        self.adjust_stock(serial=u"my-fp3-1", location=loc_new)
        self.adjust_stock(serial=u"my-fp3-2", location=loc_new)
        self.adjust_stock(serial=u"my-fp3-3", location=loc_rep)

        product2 = self.stockable_product.copy()

        defaults, possibilities = self.prepare_wizard(
            "outward", user_choices={"location_id": loc_new.id})

        # Check defaults of issue_id, date, product_id
        self.assertEqual(defaults["issue_id"], self.issue.id)
        self.assertDatetimeAlmostEqual(defaults["date"], fields.Datetime.now())
        self.assertEqual(defaults["product_id"],
                         self.stockable_product.product_variant_id.id)

        # Check domains of location_id, product_id, quant_id
        self.assertEqual(
            sorted(possibilities["location_id"].get_xml_id().values()),
            [u"commown_devices.stock_location_fp3_new",
             u"commown_devices.stock_location_fp3_repackaged"])
        self.assertEqual(
            possibilities["product_id"],
            (self.stockable_product | product2).mapped("product_variant_id"))
        self.assertEqual(
            sorted(possibilities["quant_id"].mapped("lot_id.name")),
            [u"my-fp3-1", u"my-fp3-2"])

        # Check with another user choice for location_id
        defaults, possibilities = self.prepare_wizard(
            "outward", user_choices={"location_id": loc_rep.id})

        self.assertEqual(
            possibilities["quant_id"].mapped("lot_id.name"), [u"my-fp3-3"])

    def test_create_outward_picking(self):
        # Test setup
        loc_new = self.env.ref("commown_devices.stock_location_fp3_new")
        self.adjust_stock(serial=u"my-fp3", location=loc_new)

        # Check prerequisite
        self.assertFalse(self.issue.contract_id.picking_ids)

        # Create the wizard and the picking
        vals, possibilities = self.prepare_wizard(
            "outward", user_choices={"location_id": loc_new.id})
        vals.update({k: v[0].id for k, v in possibilities.items()})
        wizard = self.env["project.issue.outward.picking.wizard"].create(vals)
        wizard.create_picking()

        # Check resulting picking
        picking = self.issue.contract_id.picking_ids
        self.assertEqual(len(picking), 1)
        self.assertEqual(picking.state, u"assigned")
        self.assertEqual(picking.move_type, u"direct")

        partner = self.issue.partner_id
        move = picking.move_lines
        self.assertEqual(len(move), 1)
        self.assertEqual(move.location_id, loc_new)
        self.assertEqual(move.location_dest_id, partner.property_stock_customer)
        self.assertEqual(picking.move_lines.mapped("lot_ids.name"), [u"my-fp3"])

    def test_inward_defaults_and_domains(self):
        # Test setup: 2 devices at the customer's location, 1 somewhere else
        partner = self.issue.partner_id
        loc_new = self.env.ref("commown_devices.stock_location_fp3_new")
        self.adjust_stock(serial=u"my-fp3-1",
                          location=partner.property_stock_customer)
        self.adjust_stock(serial=u"my-fp3-2",
                          location=partner.property_stock_customer)
        self.adjust_stock(serial=u"my-fp3-3", location=loc_new)

        defaults, possibilities = self.prepare_wizard(
            "inward", user_choices={"location_id": loc_new.id})

        # Check defaults and domains
        self.assertEqual(defaults["issue_id"], self.issue.id)
        self.assertEqual(
            sorted(possibilities["quant_id"].mapped("lot_id.name")),
            [u"my-fp3-1", u"my-fp3-2"])
        self.assertEqual(
            possibilities["location_dest_id"].mapped("name"),
            [u"Fairphone 3/3+ to check/ diagnose"])

    def test_create_inward_picking(self):
        partner = self.issue.partner_id
        self.adjust_stock(serial=u"my-fp3",
                          location=partner.property_stock_customer)

        # Create the wizard and the picking
        vals, possibilities = self.prepare_wizard("inward")
        vals.update({k: v[0].id for k, v in possibilities.items()})
        wizard = self.env["project.issue.inward.picking.wizard"].create(vals)
        wizard.create_picking()

        # Check resulting picking
        picking = self.issue.contract_id.picking_ids
        self.assertEqual(len(picking), 1)
        self.assertEqual(picking.state, u"assigned")
        self.assertEqual(picking.move_type, u"direct")

        loc_check = self.env.ref("commown_devices.stock_location_fp3_to_check")
        move = picking.move_lines
        self.assertEqual(len(move), 1)
        self.assertEqual(move.location_id, partner.property_stock_customer)
        self.assertEqual(move.location_dest_id, loc_check)
        self.assertEqual(picking.move_lines.mapped("lot_ids.name"), [u"my-fp3"])
