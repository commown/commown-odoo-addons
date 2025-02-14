from odoo import fields
from odoo.tests.common import SavepointCase


class DeviceAssignmentBaseTC(SavepointCase):
    """Base test case with common setup for device assignment tests"""

    def setUp(self):
        super().setUp()

        self.company = self.env.ref("base.res_partner_1")
        self.partner1 = self.env.ref("base.partner_demo_portal")
        self.partner1.parent_id = self.company.id
        self.partner2 = self.env.ref("base.res_partner_address_16")

        self.product_tmpl = self.env["product.template"].create(
            {
                "name": "Test Device",
                "type": "product",
                "tracking": "serial",
            }
        )
        self.product = self.product_tmpl.product_variant_id

        self.lot = self.env["stock.production.lot"].create(
            {
                "name": "test-lot",
                "product_id": self.product.id,
            }
        )

    def create_assignment(self, partner=None, date=None, device_name=None, active=True):
        """Helper method to create an assignment"""
        if partner is None:
            partner = self.partner1

        if date is None:
            date = fields.Datetime.now()

        values = {
            "device_id": self.lot.id,
            "partner_id": partner.id,
            "assignment_date": date,
            "active": active,
        }

        if device_name:
            values["device_name"] = device_name

        return self.env["customer_device_manager.device_assignment"].create(values)


class DeviceAssignmentTC(DeviceAssignmentBaseTC):
    def test_partner_update_creates_history_line(self):
        date1 = fields.Datetime.from_string("2023-01-01 10:00:00")
        assignment = self.create_assignment(date=date1)
        self.assertEqual(len(assignment.history_ids), 1)

        assignment.update({"partner_id": self.partner2.id})
        self.assertEqual(len(assignment.history_ids), 2)

        history_dates = assignment.history_ids.mapped("date")
        self.assertEqual(history_dates, sorted(history_dates, reverse=True))

    def test_name_get(self):
        assignment = self.create_assignment()
        self.assertIn(assignment.device_id.name, assignment.display_name)


class DeviceAssignmentHistoryTC(DeviceAssignmentBaseTC):
    def setUp(self):
        super().setUp()

        self.assignment = self.create_assignment(
            partner=self.partner1,
        )

        self.history_record = self.assignment.history_ids[0]

    def test_device_status_computation(self):
        self.assertEqual(self.history_record.device_status, "in_house")

        self.assignment.active = False
        self.assertEqual(self.history_record.device_status, "returned")

        self.assignment.active = True
        self.assertEqual(self.history_record.device_status, "in_house")

    def test_name_get_method(self):
        """Test the name_get method of history records"""
        result = self.history_record.name_get()
        self.assertEqual(result[0][0], self.history_record.id)
        self.assertEqual(result[0][1], "test-lot")

        self.assignment.device_name = False
        result = self.history_record.name_get()
        self.assertEqual(result[0][0], self.history_record.id)
        self.assertEqual(result[0][1], str(self.assignment.id))

        self.assertEqual(self.history_record.display_name, str(self.assignment.id))
