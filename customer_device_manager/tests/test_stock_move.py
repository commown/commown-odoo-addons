from odoo.exceptions import AccessError
from odoo.tests.common import SavepointCase

from odoo.addons.commown_devices.models.common import do_new_transfer, internal_picking
from odoo.addons.commown_devices.tests.common import create_lot_and_quant


class StockMoveTC(SavepointCase):
    def setUp(self):
        super().setUp()

        self.partner = self.env.ref("base.partner_demo_portal")
        self.company = self.env.ref("base.res_partner_1")
        self.assertTrue(self.company.is_company)
        self.partner.parent_id = self.company.id

        self.contract = self.env["contract.contract"].create(
            {"name": "Contract", "partner_id": self.partner.id}
        )
        parent_loc = self.env.ref("commown_devices.stock_location_available_for_rent")
        self.stock_location = self.env["stock.location"].create(
            {"name": "Test Loc", "usage": "internal", "location_id": parent_loc.id}
        )

        product = self.env["product.product"].create(
            {"name": "Test product", "type": "product", "tracking": "serial"}
        )
        self.lot = create_lot_and_quant(self.env, "lot", product, self.stock_location)

        group_assigner = self.env.ref(
            "customer_device_manager.group_customer_device_assigner"
        )
        self.customer_device_assigner = self.env["res.users"].create(
            {
                "name": "Customer device assigner",
                "login": "customer_device_assigner",
                "partner_id": self.partner.id,
                "groups_id": [(6, 0, [group_assigner.id])],
            }
        )

        group_portal = self.env.ref("base.group_portal")
        self.customer_employee = self.env["res.users"].create(
            {
                "name": "Customer employee",
                "login": "customer_employee",
                "partner_id": self.partner.id,
                "groups_id": [(6, 0, [group_portal.id])],
            }
        )

        self.internal_user = self.env.ref("base.group_user")

    def get_assignments(self, lot, company):
        """Find device assignments for a lot and company, including assignments to contacts of the company."""
        assignments = self.env["customer_device_manager.device_assignment"].search(
            [
                ("device_id", "=", lot.id),
            ]
        )
        return assignments.filtered(
            lambda a: a.partner_id.commercial_partner_id
            == company.commercial_partner_id
        )

    def _send(self, lot, orig, dest):
        moves = internal_picking(lot, {}, None, orig, dest, False)
        picking = moves[0].picking_id
        do_new_transfer(picking, picking.scheduled_date)
        return picking

    def test_device_assignment_lifecycle(self):
        """
        Test the lifecycle of a device assignment:
        - Send the device.
        - Update the assignment as a customer assigner.
        - Receive the device.
        - Check that an history line is created at each step
        """
        # Check test prerequisite, no assignment exists
        self.assertFalse(self.get_assignments(self.lot, self.company))

        self.contract.send_devices(self.lot, {}, do_transfer=True)
        assignment = self.get_assignments(self.lot, self.company)
        self.assertEqual(len(assignment), 1)
        self.assertEqual(assignment.device_location, "at_customer")
        self.assertEqual(len(assignment.history_ids), 1)

        with self.assertRaises(AccessError):
            assignment.sudo(self.customer_employee).update(
                {
                    "assignment_notes": "Attempt to update as a customer employee",
                }
            )

        assignment.sudo(self.customer_device_assigner).update(
            {
                "partner_id": self.partner.id,
                "assignment_notes": "Update as a customer assigner",
            }
        )
        self.assertEqual(assignment.assignment_notes, "Update as a customer assigner")
        self.assertEqual(len(assignment.history_ids), 2)

        loc_to_check = self.env.ref("commown_devices.stock_location_devices_to_check")
        self.contract.receive_devices(self.lot, {}, loc_to_check, do_transfer=True)

        self.assertEqual(assignment.device_location, "at_commown")
        self.assertEqual(len(assignment.history_ids), 3)

        loc_repacked = self.env.ref(
            "commown_devices.stock_repackaged_modules_and_accessories"
        )
        picking = self._send(self.lot, loc_to_check, loc_repacked)
        self.assertEqual(picking.state, "done")

        dest_loc_parent = self.env.ref(
            "commown_devices.stock_location_available_for_rent"
        )
        dest_loc = self.env["stock.location"].search(
            [
                ("location_id", "=", dest_loc_parent.id),
                ("usage", "=", "internal"),
            ],
            limit=1,
        )

        self.lot.grade_id = self.env.ref("commown_grade.grade_D1")
        self.contract.send_devices(self.lot, {}, do_transfer=True)

        self.assertEqual(assignment, self.get_assignments(self.lot, self.company))
        self.assertEqual(assignment.device_location, "at_customer")
        self.assertEqual(len(assignment.history_ids), 4)
