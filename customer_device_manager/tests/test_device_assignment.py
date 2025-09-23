from odoo import fields
from odoo.tests.common import TransactionCase


class DeviceAssignmentBaseTC(TransactionCase):
    """Base test case with common setup for device assignment tests"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company = cls.env.ref("base.res_partner_1")
        cls.partner1 = cls.env.ref("base.partner_demo_portal")
        cls.partner1.parent_id = cls.company.id
        cls.partner2 = cls.env.ref("base.res_partner_address_16")

        cls.product_tmpl = cls.env["product.template"].create(
            {
                "name": "Test Device",
                "type": "product",
                "tracking": "serial",
            }
        )
        cls.product = cls.product_tmpl.product_variant_id

        cls.lot = cls.env["stock.lot"].create(
            {
                "name": "test-lot",
                "product_id": cls.product.id,
            }
        )

    def create_assignment(self, partner=None, date=None, device_location="at_customer"):
        """Helper method to create an assignment"""
        if partner is None:
            partner = self.partner1

        if date is None:
            date = fields.Datetime.now()

        values = {
            "device_id": self.lot.id,
            "partner_id": partner.id,
            "assignment_date": date,
            "device_location": device_location,
        }

        return self.env["customer_device_manager.device_assignment"].create(values)


class DeviceAssignmentTC(DeviceAssignmentBaseTC):
    def test_partner_update_creates_history_line(self):
        date1 = fields.Datetime.from_string("2023-01-01 10:00:00")
        assignment = self.create_assignment(date=date1)
        self.assertEqual(len(assignment.history_ids), 1)

        assignment.update({"partner_id": self.partner2.id})
        self.assertEqual(len(assignment.history_ids), 2)

        assignment.invalidate_recordset()
        history_dates = assignment.history_ids.mapped("date")
        self.assertEqual(history_dates, sorted(history_dates, reverse=True))

    def test_name_get(self):
        assignment = self.create_assignment()
        self.assertIn(assignment.device_id.name, assignment.display_name)

    def test_date_update_history_date(self):
        date1 = fields.Datetime.from_string("2023-01-01 10:00:00")
        date2 = fields.Datetime.from_string("2023-02-01 10:00:00")

        assignment = self.create_assignment()
        first_history_line = assignment.history_ids

        self.assertNotEqual(assignment.assignment_date, date1)
        first_history_line.date = date1
        self.assertEqual(assignment.assignment_date, date1)

        assignment.update({"partner_id": self.partner2.id})
        new_date = assignment.assignment_date
        self.assertTrue(new_date > date2)

        first_history_line.date = date2
        self.assertEqual(assignment.assignment_date, new_date)

        second_history_line = (assignment.history_ids - first_history_line).ensure_one()
        second_history_line.date = date2
        self.assertEqual(assignment.assignment_date, date2)


class DeviceAssignmentHistoryTC(DeviceAssignmentBaseTC):
    def test_name_get(self):
        "Test the name_get method of history items from assignment creation and update"

        assignment = self.create_assignment(
            date=fields.Datetime.from_string("2023-01-01 10:00:00"),
            partner=self.partner1,
        )

        self.assertEqual(
            assignment.history_ids[0].display_name,
            "test-lot - Joel Willis (2023-01-01 10:00:00)",
        )

        now = fields.Datetime.now()
        assignment.update({"partner_id": self.partner2.id})
        assignment.invalidate_recordset()

        self.assertEqual(
            assignment.history_ids[0].display_name,
            "test-lot - Nicole Ford (%s)" % fields.Datetime.to_string(now),
        )
