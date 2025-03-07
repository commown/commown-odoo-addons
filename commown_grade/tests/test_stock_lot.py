import json

from odoo.tests.common import TransactionCase


class StockProductionLotTC(TransactionCase):
    def setUp(self):
        super().setUp()
        self.lot = self.env.ref("stock.lot_product_cable_management")

    def get_notify(self, old_infos=None, level="info"):
        param_name = "notify_" + level + "_channel_name"
        name = getattr(self.env.user, param_name)
        objs = self.env["bus.bus"].search([("channel", "=", name)], order="id")
        msgs = [json.loads(m)["payload"][0]["message"] for m in objs.mapped("message")]
        return msgs[len(old_infos or ()) :]

    def test_compute_grade_id(self):
        # Check pre-requisite
        self.assertFalse(self.lot.grade_id)

        grade = self.env.ref("commown_grade.grade_A0")
        self.env["commown_grade.grade_history_line"].create(
            {"lot_id": self.lot.id, "grade_id": grade.id, "date": "2000-01-01"}
        )
        # Check result
        self.assertEqual(self.lot.grade_id, grade)

        # Add new grade history line
        grade2 = self.env.ref("commown_grade.grade_A2")
        line2 = self.env["commown_grade.grade_history_line"].create(
            {"lot_id": self.lot.id, "grade_id": grade2.id}
        )

        # Check result
        self.assertEqual(self.lot.grade_id, grade2)

        line2.date = "1999-01-01"

        # Check result
        self.assertEqual(self.lot.grade_id, grade)

    def test_inverse_grade_id(self):
        grade = self.env.ref("commown_grade.grade_A1")

        # Check pre-requisite
        self.assertFalse(self.env["commown_grade.grade_history_line"].search([]))

        self.lot.grade_id = grade.id

        lot_lines = self.lot.grade_history_line_ids
        self.assertEqual(len(lot_lines), 1)
        self.assertEqual(lot_lines.grade_id, grade)

    def test_compute_grade_history_line_ids(self):
        grade = self.env.ref("commown_grade.grade_A0")
        line = self.env["commown_grade.grade_history_line"].create(
            {"lot_id": self.lot.id, "grade_id": grade.id, "date": "2000-01-01"}
        )
        self.lot._compute_grade_history_line_ids()
        self.assertEqual(self.lot.grade_history_line_ids, line)

    def test_notify_when_grade_improve(self):
        # Improve coverage in onchange
        self.lot._onchange_grade_id()

        grade0 = self.env.ref("commown_grade.grade_A0")
        grade1 = self.env.ref("commown_grade.grade_A1")

        self.lot.grade_id = grade1.id

        # Improve grade
        self.lot.grade_id = grade0.id

        old_infos = self.get_notify(level="info")
        self.lot._onchange_grade_id()
        new_infos = self.get_notify(old_infos, "info")

        expected_message = (
            "New grade is better than the last known grade, are you sure of"
            " this change?"
        )
        self.assertEqual(
            new_infos,
            [expected_message],
        )

        self.lot.grade_id = grade1.id
        old_infos = self.get_notify(level="info")
        self.lot._onchange_grade_id()
        new_infos = self.get_notify(old_infos, "info")
        self.assertFalse(new_infos)
