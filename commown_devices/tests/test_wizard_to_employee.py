from odoo.exceptions import UserError
from odoo.tests.common import SavepointCase

from .common import create_lot_and_quant


class WizardProjectTaskToEmployeeTC(SavepointCase):
    def setUp(self):
        super().setUp()
        pid = self.env["project.project"].create({"name": "Test"}).id
        partner = self.env["res.partner"].create({"name": "p1", "parent_id": 1})

        self.task = self.env["project.task"].create(
            {"name": "test", "project_id": pid, "partner_id": partner.id}
        )

        new_dev_loc = self.env.ref("commown_devices.stock_location_new_devices")
        self.loc = self.env["stock.location"].create(
            {"name": "new_fp", "usage": "internal", "location_id": new_dev_loc.id}
        )
        pt = self.env["product.template"].create(
            {"name": "FP3", "type": "product", "tracking": "serial"}
        )
        self.lot = create_lot_and_quant(
            self.env, "fp3_1", pt.product_variant_id, self.loc
        )

    def get_wizard(self):
        return self.env["project.task.to.employee.wizard"].create(
            {"task_id": self.task.id, "lot_id": self.lot.id}
        )

    def test_ok(self):
        contract = self.get_wizard().execute()

        self.assertEqual(contract.lot_ids, self.lot)
        self.assertEqual(contract.partner_id.name, "p1")
        self.assertEqual(self.task.partner_id.name, "p1")
        self.assertEqual(self.task.lot_id, self.lot)
        self.assertEqual(self.task.contract_id, contract)
        quant = (
            self.env["stock.quant"]
            .search([("lot_id", "=", self.lot.id)])
            .filtered(lambda q: q.quantity > q.reserved_quantity)
        )
        self.assertEqual(quant.location_id.partner_id, self.task.partner_id)
        self.assertEqual(
            quant.location_id.location_id,
            self.env.ref("stock.stock_location_customers"),
        )

    def test_lot_domain(self):
        wizard = self.get_wizard()
        self.assertEqual(self.lot.search(wizard._domain_lot_id()), self.lot)

        lot2 = create_lot_and_quant(self.env, "fp3_2", self.lot.product_id, self.loc)
        self.assertEqual(self.lot.search(wizard._domain_lot_id()), self.lot | lot2)

    def test_error_device_not_available(self):
        quant = self.env["stock.quant"].search([("lot_id", "=", self.lot.id)])
        self.assertEqual(len(quant), 1)  # Test pre-requisite

        quant.reserved_quantity = 1
        with self.assertRaises(UserError) as err:
            self.get_wizard().execute()
        self.assertEqual(
            err.exception.name, "Cannot find given device. Is it really available?"
        )

    def test_error_no_partner(self):
        self.task.partner_id = False
        with self.assertRaises(UserError) as err:
            self.get_wizard().execute()

    def test_error_not_an_employee(self):
        self.task.partner_id = self.env.ref("base.partner_demo_portal").id
        with self.assertRaises(UserError) as err:
            self.get_wizard().execute()
