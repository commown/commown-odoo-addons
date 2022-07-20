from mock import patch

from odoo.tests.common import at_install, post_install

from odoo.addons.account_invoice_merge_auto_pay.tests.common import (
    AutoPayInvoiceTC,
    fake_do_tx_ok,
)
from odoo.addons.payment.models.payment_acquirer import PaymentTransaction


@at_install(False)
@post_install(True)
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
