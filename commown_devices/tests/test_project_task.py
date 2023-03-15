import datetime

from odoo.exceptions import ValidationError

from ..models.common import do_new_transfer
from .common import DeviceAsAServiceTC


class ProjectTaskPickingTC(DeviceAsAServiceTC):
    def _create_xml_id(self, record, name):
        return self.env["ir.model.data"].create(
            {
                "module": "commown_devices",
                "name": name,
                "model": record._name,
                "res_id": record.id,
            }
        )

    def setUp(self):
        super().setUp()

        self.project = self.env["project.project"].create({"name": "Test"})
        self.task = self.env["project.task"].create(
            {"name": "test", "project_id": self.project.id}
        )  # for wizard tests

        self.partner2 = self.so.partner_id.copy({"name": "test partner2"})
        self.so2 = self.so.copy({"partner_id": self.partner2.id})
        self.so2.action_confirm()

        self.storable_product2 = self.storable_product.copy({"name": "Core-X4"})
        cc = self.storable_product2.product_variant_ids

        contract_model = self.env["contract.contract"]
        self.c1, self.c2, self.c3 = contract_model.of_sale(self.so)

        self._create_and_send_device("fp1", self.c1)
        self._create_and_send_device("fp2", self.c2)
        self._create_and_send_device("fp3", self.c3)
        self._create_and_send_device("fp4", None)
        self._create_and_send_device("cc1", self.c1, cc)
        self._create_and_send_device("cc2", None, cc)
        self._create_and_send_device("cc3", self.c3, cc, do_transfer=False)

        self.task_test_checks = self.env["project.task"].create(
            {
                "name": "test task",
                "project_id": self.project.id,
                "contract_id": self.c1.id,
            }
        )  # for checks on stage change tests
        self.task_test_checks2 = self.env["project.task"].create(
            {
                "name": "test task 2",
                "project_id": self.project.id,
                "contract_id": self.c2.id,
            }
        )  # for checks on stage change tests

        # Create stage to assign xml_ids so constrains on stage_id pass
        t1, t2 = self.env["project.task.type"].create(
            [
                {"name": "t1"},
                {"name": "t2"},
            ]
        )
        self.ongoing_stage = self.env.ref("commown_devices.sup_picking_ongoing_stage")
        self.picking_sent_stage = self.env.ref("commown_devices.picking_sent")

        # Create a unused product and an unused service
        self.env["product.template"].create(
            {"name": "unused product", "type": "product", "tracking": "none"}
        )
        self.env["product.template"].create(
            {"name": "unused serial", "type": "product", "tracking": "serial"}
        )
        self.env["product.template"].create(
            {"name": "unused service", "type": "service"}
        )

        self.nontracked_product = self.env["product.template"].create(
            {
                "name": "non tracked product (Module)",
                "type": "product",
                "tracking": "none",
            }
        )
        location = self.env["stock.location"].create(
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
            self.nontracked_product.product_variant_id, location
        )

    def _create_and_send_device(self, serial, contract, product=None, do_transfer=True):
        lot = self.adjust_stock(product, serial=serial)
        if contract is not None:
            quant = lot.quant_ids.filtered(lambda q: q.quantity > 0)
            contract.send_device(quant.ensure_one(), do_transfer=do_transfer)

    def get_form(self, **user_choices):
        return self.prepare_ui(
            "project.task", self.project, "project_id", user_choices=user_choices
        )

    def test_ui_help_desk(self):
        self.project.update({"device_tracking": True, "require_contract": True})

        partner = self.so.partner_id
        product1 = self.storable_product.product_variant_ids[0]
        product2 = self.storable_product2.product_variant_ids[0]

        # Set partner only
        values, choices = self.get_form(
            partner_id=partner.id,
            commercial_partner_id=partner.commercial_partner_id.id,
        )

        # > check values
        self.assertEqual(values.get("project_id"), self.project.id)
        self.assertEqual(values.get("partner_id"), partner.id)
        self.assertFalse(values.get("storable_product_id"))
        self.assertFalse(values.get("contract_id"))
        self.assertFalse(values.get("lot_id"))

        # > check domains
        self.assertEqual(choices["contract_id"], self.c1 | self.c2 | self.c3)
        self.assertEqual(choices["storable_product_id"], product1 | product2)
        lot_names = set(choices["lot_id"].mapped("name"))
        self.assertEqual(lot_names, {"fp1", "fp2", "fp3", "cc1", "cc3"})

        # Set contract only (contract 1: two device choice)
        values, choices = self.get_form(contract_id=self.c1.id)

        # > check values
        self.assertEqual(values.get("project_id"), self.project.id)
        self.assertEqual(values.get("partner_id"), partner.id)
        self.assertEqual(values.get("contract_id"), self.c1.id)
        self.assertFalse(values.get("storable_product_id"))
        self.assertFalse(values.get("lot_id"))

        # > check domains
        self.assertTrue(len(choices["partner_id"]) > 1)  # no contract filtering
        self.assertEqual(choices["contract_id"], self.c1 | self.c2 | self.c3)
        self.assertEqual(choices["storable_product_id"], product1 | product2)
        self.assertEqual(set(choices["lot_id"].mapped("name")), {"fp1", "cc1"})

        # Set contract only (contract 2: single device choice)
        values, choices = self.get_form(contract_id=self.c2.id)

        # > check values
        self.assertEqual(values.get("storable_product_id"), product1.id)
        ui_lots = self.env["stock.production.lot"].browse(values["lot_id"])
        self.assertEqual(ui_lots.mapped("name"), ["fp2"])

        # Set lot_id only
        lot = self.env["stock.production.lot"].search([("name", "=", "cc1")])
        values, choices = self.get_form(lot_id=lot.id)

        # > check values
        self.assertEqual(values.get("project_id"), self.project.id)
        self.assertEqual(values.get("partner_id"), partner.id)
        self.assertEqual(values.get("contract_id"), self.c1.id)
        self.assertEqual(values.get("storable_product_id"), product2.id)
        self.assertEqual(values.get("lot_id"), lot.id)

        # > check domains
        self.assertTrue(len(choices["partner_id"]) > 1)
        self.assertEqual(choices["contract_id"], self.c1 | self.c2 | self.c3)
        self.assertEqual(choices["storable_product_id"], product1 | product2)
        self.assertEqual(choices["lot_id"].mapped("name"), ["cc1"])

    def test_ui_repair(self):
        self.project.update({"device_tracking": True, "require_contract": False})
        self._create_and_send_device("fp5", None)

        product = self.storable_product.product_variant_ids[0]

        # Set product only
        values, choices = self.get_form(storable_product_id=product.id)

        # > check values
        self.assertEqual(values.get("project_id"), self.project.id)
        self.assertFalse(values.get("partner_id"))
        self.assertEqual(values.get("storable_product_id"), product.id)
        self.assertFalse(values.get("contract_id"))
        self.assertFalse(values.get("lot_id"))

        # > check domains
        choice_names = set(choices["storable_product_id"].mapped("name"))
        self.assertTrue(
            {"Core-X4", "Fairphone 3", "unused product"}.issubset(choice_names)
        )
        self.assertNotIn("unused service", choice_names)

        lot_names = set(choices["lot_id"].mapped("name"))
        self.assertEqual(lot_names, {"fp4", "fp5"})

        # Set lot_id only
        lot = self.env["stock.production.lot"].search([("name", "=", "cc2")])
        values, choices = self.get_form(lot_id=lot.id)

        # > check values
        self.assertEqual(values.get("project_id"), self.project.id)
        self.assertFalse(values.get("partner_id"))
        self.assertFalse(values.get("contract_id"))
        self.assertEqual(values.get("storable_product_id"), lot.product_id.id)
        self.assertEqual(values.get("lot_id"), lot.id)

        # > check domains
        choice_names = set(choices["storable_product_id"].mapped("name"))
        self.assertTrue(
            {"Core-X4", "Fairphone 3", "unused product"}.issubset(choice_names)
        )
        self.assertNotIn("unused service", choice_names)
        lot_names = set(choices["lot_id"].mapped("name"))
        self.assertEqual(lot_names, {"cc2", "cc3"})

    def test_wizard_involved(self):

        self.task.contract_id = self.c1
        self.task.lot_id = self.task.contract_id.quant_ids[0].lot_id

        values, possible_values = self.prepare_ui(
            "project.task.involved_device_picking.wizard", self.task, "task_id"
        )

        self.assertEqual(
            values["present_location_id"],
            self.task.lot_id.quant_ids.filtered(
                lambda q: q.quantity > 0
            ).location_id.id,
        )

        # Create a picking and check the lot location at the end of the picking
        date = datetime.datetime(2020, 1, 10, 16, 2, 34)
        wizard = self.env["project.task.involved_device_picking.wizard"].create(
            {
                "task_id": self.task.id,
                "date": date,
                "location_dest_id": possible_values["location_dest_id"][0].id,
                "present_location_id": values["present_location_id"],
            }
        )
        wizard.create_picking()

        self.assertEqual(
            self.task.lot_id.quant_ids.filtered(
                lambda q: q.quantity > 0
            ).location_id.id,
            possible_values["location_dest_id"][0].id,
        )

        # Check that the new location of the lot is no longer available as destination
        values, possible_values = self.prepare_ui(
            "project.task.involved_device_picking.wizard", self.task, "task_id"
        )

        self.assertNotIn(
            values["present_location_id"],
            possible_values["location_dest_id"].mapped("id"),
        )

    def test_wizard_outward_with_task_only(self):
        values, possible_values = self.prepare_ui(
            "project.task.outward.picking.wizard", self.task, "task_id"
        )

        self.assertEqual(values["task_id"], self.task.id)

        self.assertEqual(
            sorted(possible_values["product_tmpl_id"].mapped("name")),
            ["Core-X4", "Fairphone 3", "unused serial"],
        )
        self.assertEqual(
            sorted(possible_values["lot_id"].mapped("name")), ["cc2", "cc3", "fp4"]
        )

    def test_wizard_outward_with_product_tmpl(self):

        values, possible_values = self.prepare_ui(
            "project.task.outward.picking.wizard",
            self.task,
            "task_id",
            {"product_tmpl_id": self.storable_product.id},
        )

        self.assertEqual(values["task_id"], self.task.id)
        self.assertEqual(values["product_tmpl_id"], self.storable_product.id)

        self.assertEqual(
            sorted(possible_values["product_tmpl_id"].mapped("name")),
            ["Core-X4", "Fairphone 3", "unused serial"],
        )
        self.assertEqual(
            possible_values["variant_id"], self.storable_product.product_variant_ids
        )
        self.assertEqual(sorted(possible_values["lot_id"].mapped("name")), ["fp4"])

    def test_wizard_outward_with_product_variant(self):

        variant = self.storable_product.product_variant_ids[0]
        values, possible_values = self.prepare_ui(
            "project.task.outward.picking.wizard",
            self.task,
            "task_id",
            {"variant_id": variant.id},
        )

        self.assertEqual(values["task_id"], self.task.id)
        self.assertEqual(values["product_tmpl_id"], self.storable_product.id)
        self.assertEqual(values["variant_id"], variant.id)

        self.assertEqual(
            sorted(possible_values["product_tmpl_id"].mapped("name")),
            ["Core-X4", "Fairphone 3", "unused serial"],
        )
        self.assertEqual(
            possible_values["variant_id"], self.storable_product.product_variant_ids
        )
        self.assertEqual(sorted(possible_values["lot_id"].mapped("name")), ["fp4"])

        # Actually create a picking
        self.task.update(
            {"contract_id": self.c1.id, "lot_id": self.c1.quant_ids[0].lot_id}
        )

        date = datetime.datetime(2020, 1, 10, 16, 2, 34)
        wizard = self.env["project.task.outward.picking.wizard"].create(
            {
                "task_id": self.task.id,
                "date": date,
                "lot_id": self.task.lot_id.id,
                "variant_id": self.task.lot_id.product_id.id,
                "product_tmpl_id": self.task.lot_id.product_id.product_tmpl_id.id,
            }
        )
        picking = wizard.create_picking()

        self.assertEqual(picking.scheduled_date, date)
        self.assertEqual(picking.date_done, date)

    def test_wizard_inward(self):

        self.task.contract_id = self.c1

        values, possible_values = self.prepare_ui(
            "project.task.inward.picking.wizard", self.task, "task_id"
        )

        self.assertEqual(values["task_id"], self.task.id)
        self.assertFalse(values.get("lot_id"))

        self.assertEqual(
            sorted(possible_values["lot_id"].mapped("name")), ["cc1", "fp1"]
        )

    def test_wizard_contract_transfer(self):
        self.task.update(
            {
                "contract_id": self.c1.id,
                "lot_id": self.c1.quant_ids[0].lot_id,
            }
        )
        self.assertIn(self.task.lot_id, self.c1.mapped("quant_ids.lot_id"))
        self.assertNotIn(self.task.lot_id, self.c2.mapped("quant_ids.lot_id"))

        wizard = self.env["project.task.contract_transfer.wizard"].create(
            {
                "task_id": self.task.id,
                "contract_id": self.c2.id,
            }
        )
        wizard.create_transfer()

        self.assertNotIn(self.task.lot_id, self.c1.mapped("quant_ids.lot_id"))
        self.assertIn(self.task.lot_id, self.c2.mapped("quant_ids.lot_id"))

    def test_contract_resiliation_with_devices(self):
        diagnostic_stage = self.env.ref("commown_devices.diagnostic_stage")
        resiliated_stage = self.env.ref("commown_devices.resiliated_stage")

        self.assertTrue(self.c1.quant_nb > 0)
        expected_message = (
            "Error while validating constraint\n\nThese tasks can not be moved forward. There are still device(s) "
            "associated with their contract: %s\n" % self.task_test_checks.ids
        )

        with self.assertRaises(ValidationError) as err1:
            self.task_test_checks.stage_id = diagnostic_stage
        self.assertEqual(expected_message, err1.exception.name)

        with self.assertRaises(ValidationError) as err2:
            self.task_test_checks.stage_id = resiliated_stage
        self.assertEqual(expected_message, err2.exception.name)

        self.task_test_checks.contract_id.quant_ids.unlink()
        self.task_test_checks.contract_id._compute_quant_ids()

        self.task_test_checks.stage_id = diagnostic_stage
        self.assertTrue(self.task_test_checks.stage_id == diagnostic_stage)

        self.task_test_checks.stage_id = resiliated_stage
        self.assertTrue(self.task_test_checks.stage_id == resiliated_stage)

    def test_outward_inward_notracking(self):
        def get_present_location(pt_variant):
            return (
                self.env["stock.quant"]
                .search(
                    [
                        ("product_id.id", "=", pt_variant.id),
                        ("quantity", ">", "0"),
                    ]
                )
                .location_id
            )

        self.task.contract_id = self.c1
        date = datetime.datetime(2020, 1, 10, 16, 2, 34)
        pt_variant = self.nontracked_product.product_variant_id

        initial_location = get_present_location(pt_variant)
        wizard_outward = self.env[
            "project.task.notracking.outward.picking.wizard"
        ].create({"task_id": self.task.id, "date": date, "variant_id": pt_variant.id})

        picking = wizard_outward.create_picking()
        do_new_transfer(picking, date)

        client_location = get_present_location(pt_variant)
        self.assertNotEqual(initial_location, client_location)

        wizard_inward = self.env[
            "project.task.notracking.inward.picking.wizard"
        ].create({"task_id": self.task.id, "date": date, "variant_id": pt_variant.id})

        picking = wizard_inward.create_picking()
        do_new_transfer(picking, date)

        final_location = get_present_location(pt_variant)
        self.assertEqual(
            final_location,
            self.env.ref("commown_devices.stock_location_devices_to_check"),
        )

    def test_change_stage_check(self):

        with self.assertRaises(ValidationError) as err:
            self.task_test_checks.stage_id = self.ongoing_stage
        self.assertEqual(
            "Error while validating constraint\n\nThese tasks can not be moved forward. There are no picking linked to those tasks: [%s]\n"
            % self.task_test_checks.id,
            err.exception.name,
        )
        with self.assertRaises(ValidationError) as err2:
            self.task_test_checks2.stage_id = self.ongoing_stage
        self.assertEqual(
            "Error while validating constraint\n\nThese tasks can not be moved forward. There are no picking linked to those tasks: [%s]\n"
            % self.task_test_checks2.id,
            err2.exception.name,
        )
        with self.assertRaises(ValidationError) as err3:
            self.task_test_checks.stage_id = self.picking_sent_stage
        self.assertEqual(
            "Error while validating constraint\n\nThese tasks can not be moved forward. There are no picking linked to those tasks: [%s]\n"
            % self.task_test_checks.id,
            err3.exception.name,
        )

        module = self.nontracked_product.product_variant_id
        lot = self.storable_product.product_variant_id

        stock_location = self.env.ref("stock.stock_location_stock")
        quant = self.env["stock.quant"].search(
            [
                ("product_id", "=", lot.id),
                ("quantity", ">", 0),
                ("location_id", "child_of", stock_location.id),
            ]
        )[0]

        self.task_test_checks.contract_id.send_device_tracking_none(
            module,
            origin=self.task_test_checks.get_id_name(),
        )

        self.task_test_checks.stage_id = self.ongoing_stage
        self.assertTrue(self.task_test_checks.stage_id == self.ongoing_stage)

        self.task_test_checks2.contract_id.send_device(
            quant,
            origin=self.task_test_checks2.get_id_name(),
        )
        self.task_test_checks2.stage_id = self.ongoing_stage
        self.assertTrue(self.task_test_checks2.stage_id == self.ongoing_stage)

        self.task_test_checks.stage_id = self.picking_sent_stage
        self.assertTrue(self.task_test_checks.stage_id == self.picking_sent_stage)
