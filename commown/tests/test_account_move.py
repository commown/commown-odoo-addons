from unittest.mock import patch

from odoo.tests import tagged

from odoo.addons.account_invoice_merge_auto_pay.tests.common import (
    AutoPayInvoiceTC,
    fake_do_tx_ok,
)
from odoo.addons.payment.models.payment_provider import PaymentTransaction


@tagged("-at_install", "post_install")
class AccountInvoiceTC(AutoPayInvoiceTC):
    def test_user_id_ignored_in_invoice_merge(self):
        inv_1 = self.create_invoice(
            self.partner_1,
            "2019-05-09",
            payment_mode_id=self.payment_mode.id,
            user_id=self.env.user.id,
        )
        inv_2 = self.create_invoice(
            self.partner_1, "2019-05-10", payment_mode_id=self.payment_mode.id
        )

        with patch.object(PaymentTransaction, "s2s_do_transaction", fake_do_tx_ok):
            self._multiple_invoice_merge_test([inv_1, inv_2])

    def test_merge_auto_pay_sends_email(self):
        p_inv = self.partner_1.copy({"type": "invoice", "parent_id": self.partner_1.id})
        inv_1 = self.create_invoice(
            p_inv, "2019-05-09", payment_mode_id=self.payment_mode.id
        )
        inv_2 = self.create_invoice(
            p_inv, "2019-05-10", payment_mode_id=self.payment_mode.id
        )

        with patch.object(PaymentTransaction, "s2s_do_transaction", fake_do_tx_ok):
            new_inv = self._multiple_invoice_merge_test([inv_1, inv_2])

        mail = self.env["mail.mail"].search(
            [
                ("model", "=", new_inv._name),
                ("res_id", "=", new_inv.id),
                ("attachment_ids.res_name", "=", new_inv.display_name),
                ("attachment_ids.mimetype", "=", "application/pdf"),
            ]
        )
        self.assertTrue(mail)
