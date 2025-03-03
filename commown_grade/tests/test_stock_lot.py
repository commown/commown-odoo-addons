from odoo.tests.common import TransactionCase


class StockProductionLotTC(TransactionCase):
    def setUp(self):
        super().setUp()
        self.lot = self.env.ref("stock.lot_product_cable_management")

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
        self.env["commown_grade.grade_history_line"]

        # Check pre-requisite
        self.assertFalse(self.env["commown_grade.grade_history_line"].search([]))

        self.lot.grade_id = grade.id

        lot_lines = self.lot.grade_history_line_ids
        self.assertEqual(len(lot_lines), 1)
        self.assertEqual(lot_lines.grade_id, grade)
