from datetime import date

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class ResPartnerTC(TransactionCase):
    def test_merge_time_interval(self):
        comp_interval = self.env["res.partner"].invoice_merge_time_interval
        _date = date(2025, 1, 1)

        self.assertEqual(_date + comp_interval("daily", 10), date(2025, 1, 11))
        self.assertEqual(_date + comp_interval("weekly", 2), date(2025, 1, 15))
        self.assertEqual(_date + comp_interval("monthly", 2), date(2025, 3, 1))
        self.assertEqual(_date + comp_interval("monthlylastday", 2), date(2025, 3, 31))
        self.assertEqual(_date + comp_interval("yearly", 2), date(2027, 1, 1))
