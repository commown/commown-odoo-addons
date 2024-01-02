from datetime import date

from mock import patch

from odoo.tests.common import TransactionCase, at_install, post_install


@at_install(False)
@post_install(True)
class SimpleReconciliationTC(TransactionCase):
    def setUp(self):
        super(SimpleReconciliationTC, self).setUp()
        self.lines = [
            {
                "id": 1,
                "partner_id": 7,
                "date_maturity": date(2018, 1, 1),
                "credit": 2,
                "debit": 0,
            },
            {
                "id": 2,
                "partner_id": 7,
                "date_maturity": date(2018, 1, 10),
                "credit": 2,
                "debit": 0,
            },
            {
                "id": 3,
                "partner_id": 7,
                "date_maturity": date(2018, 1, 11),
                "credit": 0,
                "debit": 2,
            },
            {
                "id": 4,
                "partner_id": 7,
                "date_maturity": date(2018, 1, 21),
                "credit": 0,
                "debit": 2,
            },
        ]

    def test_without_max_reconcile_days_gap(self):
        mrs = self.env["mass.reconcile.simple.partner"]
        with patch.object(mrs, "_reconcile_lines", return_value=(True, "")):
            res = mrs.rec_auto_lines_simple(self.lines)
        self.assertEqual(res, [1, 3, 2, 4])

    def test_with_max_reconcile_days_gap(self):
        mrs = self.env["mass.reconcile.simple.partner_commown"]
        with patch.object(mrs, "_reconcile_lines", return_value=(True, "")):
            res = mrs.rec_auto_lines_simple(self.lines)
        self.assertEqual(res, [2, 3])
