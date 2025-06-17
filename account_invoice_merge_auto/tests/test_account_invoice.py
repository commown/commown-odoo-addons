import unittest

from odoo import fields
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class AccountInvoiceMergeAutoTC(AccountTestInvoicingCommon):
    "Invoice related test cases"

    @classmethod
    def setUpClass(cls):
        "Try default chart template or request a visible one and try again"
        try:
            super().setUpClass()
        except unittest.SkipTest:
            coa = cls.env["account.chart.template"].search(
                [("visible", "=", True)], limit=1
            )
            chart_template_ref = coa.get_external_id()[coa.id]
            super().setUpClass(chart_template_ref)

    def _partner_invoices(self, partner):
        return self.env["account.move"].search(
            [("partner_id", "=", partner.id), ("move_type", "=", "out_invoice")]
        )

    def create_invoice(self, partner, date, price):
        inv = self.init_invoice(
            "out_invoice",
            partner=partner,
            invoice_date=date,
            products=self.product_a,
            amounts=[price],
        )
        inv.auto_merge = True
        return inv

    def test_cron(self):
        self.partner_a.update(
            {
                "invoice_merge_next_date": "2019-05-15",
                "invoice_merge_recurring_rule_type": "monthly",
                "invoice_merge_recurring_interval": 1,
            }
        )

        inv_1 = self.create_invoice(self.partner_a, "2019-05-01", 5)
        inv_2 = self.create_invoice(self.partner_a, "2019-05-04", 10)
        inv_3 = self.create_invoice(self.partner_a, "2019-05-16", 20)
        old_invoices = self._partner_invoices(self.partner_a)

        self.env["account.move"]._cron_invoice_merge("2019-05-17")

        self.assertEqual(inv_1.state, "cancel")
        self.assertEqual(inv_2.state, "cancel")
        self.assertEqual(inv_3.state, "draft")  # after invoice_merge_next_date!

        other_inv = self._partner_invoices(self.partner_a) - old_invoices
        self.assertEqual(len(other_inv), 1)
        self.assertEqual(other_inv.amount_untaxed, 2015)
        self.assertEqual(other_inv.state, "draft")
        self.assertEqual(other_inv.date, fields.Date.from_string("2019-05-17"))
        self.assertEqual(
            self.partner_a.invoice_merge_next_date,
            fields.Date.from_string("2019-06-15"),
        )
