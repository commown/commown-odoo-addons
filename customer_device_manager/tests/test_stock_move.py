from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase

from odoo.addons.commown_devices.models.common import do_new_transfer, internal_picking
from odoo.addons.commown_devices.tests.common import create_lot_and_quant


class StockMoveTC(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        def _ref(name):
            return cls.env.ref("commown_devices.%s" % name)

        cls.loc_to_check = _ref("stock_location_devices_to_check")
        cls.loc_for_rent = _ref("stock_location_available_for_rent")
        cls.loc_repacked = _ref("stock_repackaged_modules_and_accessories")

        cls.partner = cls.env.ref("base.partner_demo_portal")
        cls.company = cls.env.ref("base.res_partner_1")
        assert cls.company.is_company
        cls.partner.parent_id = cls.company.id

        cls.contract = cls.env["contract.contract"].create(
            {"name": "Contract", "partner_id": cls.partner.id}
        )
        cls.stock_location = cls.env["stock.location"].create(
            {"name": "MyLoc", "usage": "internal", "location_id": cls.loc_for_rent.id}
        )

        product = cls.env["product.product"].create(
            {"name": "Test product", "type": "product", "tracking": "serial"}
        )
        cls.lot = create_lot_and_quant(cls.env, "lot", product, cls.stock_location)

        group_assigner = cls.env.ref(
            "customer_device_manager.group_customer_device_assigner"
        )
        cls.customer_device_assigner = cls.env["res.users"].create(
            {
                "name": "Customer device assigner",
                "login": "customer_device_assigner",
                "partner_id": cls.partner.id,
                "groups_id": [(6, 0, [group_assigner.id])],
            }
        )

        group_portal = cls.env.ref("base.group_portal")
        cls.customer_employee = cls.env["res.users"].create(
            {
                "name": "Customer employee",
                "login": "customer_employee",
                "partner_id": cls.partner.id,
                "groups_id": [(6, 0, [group_portal.id])],
            }
        )

        cls.internal_user = cls.env.ref("base.group_user")

    def get_assignments(self, lot):
        "Find device assignments for a lot"
        return self.env["customer_device_manager.device_assignment"].search(
            [("device_id", "=", lot.id)]
        )

    def _send(self, lot, orig, dest):
        moves = internal_picking(lot, {}, None, orig, dest, False)
        picking = moves[0].picking_id
        do_new_transfer(picking, picking.scheduled_date)
        return picking

    def test_device_assignment_allow_creation_on_picking_validation(self):
        "A user in the stock user group must be able to validate a picking that creates an assignment"

        user = self.env.ref("base.user_demo")
        groups = (
            self.env.ref("base.group_user")
            | self.env.ref("stock.group_stock_user")  # allow reading lots a.s.o.
            | self.env.ref("account.group_account_invoice")  # allow reading contracts
        )
        user.groups_id = [(6, 0, groups.ids)]

        picking = self.contract.send_devices(self.lot, {}).mapped("picking_id")

        # This is the actual test that must not crash:
        picking.with_user(user.id).button_validate()

    def test_device_assignment_lifecycle_same_customer(self):
        """
        Test a typical lifecycle of a device assignment:
        - Send the device.
        - Update the assignment as a customer assigner.
        - Receive the device.
        - Repack the device and resend it to the same customer.
        - Check that an history line is created at each step.
        """
        # Check test prerequisite, no assignment exists
        self.assertFalse(self.get_assignments(self.lot))

        self.contract.send_devices(self.lot, {}, do_transfer=True)
        assignment = self.get_assignments(self.lot)
        self.assertEqual(len(assignment), 1)
        self.assertEqual(assignment.device_location, "at_customer")
        self.assertEqual(assignment.partner_id, self.company)
        self.assertEqual(len(assignment.history_ids), 1)
        self.assertEqual(assignment.contract_name, self.contract.name)

        with self.assertRaises(AccessError):
            assignment.with_user(self.customer_employee).update(
                {
                    "assignment_notes": "Attempt to update as a customer employee",
                }
            )

        assignment.with_user(self.customer_device_assigner).update(
            {
                "partner_id": self.partner.id,
                "assignment_notes": "Update as a customer assigner",
            }
        )
        self.assertEqual(assignment.assignment_notes, "Update as a customer assigner")
        self.assertEqual(len(assignment.history_ids), 2)

        self.contract.receive_devices(self.lot, {}, self.loc_to_check, do_transfer=True)

        self.assertEqual(assignment.device_location, "at_commown")
        self.assertEqual(len(assignment.history_ids), 3)

        picking = self._send(self.lot, self.loc_to_check, self.loc_repacked)
        self.assertEqual(picking.state, "done")

        self.lot.grade_id = self.env.ref("commown_grade.grade_D1")
        self.contract.send_devices(self.lot, {}, do_transfer=True)

        self.assertEqual(assignment, self.get_assignments(self.lot))
        self.assertEqual(assignment.device_location, "at_customer")
        self.assertEqual(len(assignment.history_ids), 4)

    def test_device_assignment_lifecycle_another_customer(self):
        """
        Test another lifecycle of a device assignment:
        - Send the device.
        - Receive the device.
        - Repack the device and resend it to another customer.
        - Check the assignements and their history from each customer's point of view
        """

        # Send the device to a first company and check the history
        self.contract.send_devices(self.lot, {}, do_transfer=True)

        assignment = self.get_assignments(self.lot)
        self.assertEqual(len(assignment), 1)
        self.assertEqual(assignment.device_location, "at_customer")
        self.assertEqual(assignment.partner_id, self.company)
        self.assertEqual(len(assignment.history_ids), 1)
        self.assertEqual(assignment.contract_name, self.contract.name)

        # Receive the device back
        self.contract.receive_devices(self.lot, {}, self.loc_to_check, do_transfer=True)

        self.assertEqual(assignment.device_location, "at_commown")
        self.assertEqual(len(assignment.history_ids), 2)

        # Repack it
        picking = self._send(self.lot, self.loc_to_check, self.loc_repacked)
        self.lot.grade_id = self.env.ref("commown_grade.grade_D1")

        self.assertEqual(picking.state, "done")

        # Send it to another customer
        other_company = self.company.copy()
        other_partner = self.partner.copy({"parent_id": other_company.id})
        other_contract = self.env["contract.contract"].create(
            {"name": "Other contract", "partner_id": other_partner.id}
        )

        other_contract.send_devices(self.lot, {}, do_transfer=True)

        assignments = self.get_assignments(self.lot)

        self.assertEqual(len(assignments), 2)
        self.assertIn(assignment, assignments)
        self.assertEqual(assignment.device_location, "at_commown")
        self.assertEqual(assignment.partner_id, self.company)
        self.assertFalse(assignment.contract_name)
        self.assertEqual(len(assignment.history_ids), 2)

        other_assignment = assignments - assignment
        self.assertEqual(other_assignment.device_location, "at_customer")
        self.assertEqual(other_assignment.partner_id, other_company)
        self.assertEqual(other_assignment.contract_name, other_contract.name)
        self.assertEqual(len(other_assignment.history_ids), 1)
