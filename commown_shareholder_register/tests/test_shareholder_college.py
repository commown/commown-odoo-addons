from odoo.tests import TransactionCase


class TestShareholderCollege(TransactionCase):
    def test_name_get(self):
        name = "TEST"
        college = self.env["commown_shareholder_register.college"].create(
            {"name": name, "rank": 1000}
        )
        self.assertEqual(
            college.name_get(), [(college.id, "College %s" % college.name)]
        )
