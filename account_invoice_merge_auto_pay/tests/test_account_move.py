from unittest.mock import patch

from odoo import fields
from odoo.exceptions import ValidationError

from odoo.addons.account_invoice_merge_auto.tests.test_account_invoice import (
    AbstractAccountInvoiceMergeAutoTC,
)
from odoo.addons.payment.models.payment_transaction import PaymentTransaction
from odoo.addons.queue_job.tests.common import trap_jobs

from .common import inject_payment_data


def fake_do_tx_ok(self, *args, **kwargs):
    self.update({"state": "done", "provider_reference": "test-%d" % self.id})


class AccountMoveTC(AbstractAccountInvoiceMergeAutoTC):
    "Test class for this module's account move methods"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        inject_payment_data(cls)

    def _merge_and_pay(self, date="2019-05-16", expect_merge=True, expect_pay=True):
        with trap_jobs() as trap:
            invs, merge_infos = self.env["account.move"]._cron_invoice_merge(date)

        if expect_merge:
            merged_inv = self.env["account.move"].browse(list(merge_infos.keys())[0])
            self.assertEqual(len(merge_infos), 1)
        else:
            self.assertEqual(len(merge_infos), 0)
            self.assertEqual(len(invs), 1)
            merged_inv = invs

        func = merged_inv._invoice_merge_auto_pay_invoice_job
        if not expect_pay:
            trap.assert_jobs_count(0, func)
        else:
            trap.assert_jobs_count(1, func)

            with patch.object(
                PaymentTransaction,
                "_send_payment_request",
                side_effect=fake_do_tx_ok,
                autospec=True,
            ):
                trap.perform_enqueued_jobs()

        return merged_inv

    def create_default_invoices(self, **params):
        return [
            self.create_invoice(self.partner_a, date, 1.0, **params)
            for date in ("2019-05-09", "2019-05-10")
        ]

    def test_do_not_pay_refund(self):
        "Do not pay refunds, but do not prevent their merge"

        self.create_default_invoices(move_type="out_refund")
        new_inv = self._merge_and_pay(expect_pay=False)
        self.assertEqual(new_inv.payment_state, "not_paid")

    def test_auto_pay_merged_invoices(self):
        invoices = self.create_default_invoices()

        new_inv = self._merge_and_pay()

        self.assertEqual(new_inv.invoice_date, fields.Date.from_string("2019-05-16"))
        self.assertTrue(all(inv.state == "cancel" for inv in invoices))
        self.assertEqual(
            self.partner_a.invoice_merge_next_date,
            fields.Date.from_string("2019-06-15"),
        )
        self.assertEqual(new_inv.payment_state, "paid")

    def test_auto_pay_single_invoices(self):
        inv = self.create_invoice(self.partner_a, "2019-05-10", 1.0)

        self._merge_and_pay(expect_merge=False)

        self.assertEqual(inv.payment_state, "paid")
        self.assertEqual(inv.invoice_date, fields.Date.from_string("2019-05-10"))
        self.assertEqual(
            self.partner_a.invoice_merge_next_date,
            fields.Date.from_string("2019-06-15"),
        )

    def test_auto_pay_no_token_error(self):
        self.partner_a.payment_token_id = False
        self.create_default_invoices()

        with self.assertRaises(ValidationError) as err:
            self._merge_and_pay()

        self.assertIn("No payment token", err.exception.args[0])
