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

    def test_multiply_investments(self):
        account = self.env.ref("l10n_fr.1_pcg_2751")
        equity = self.env["product.product"].create(
            {
                "name": "Investment test product",
                "is_equity": True,
                "equity_type": "invest",
                "list_price": 60.0,
            }
        )
        not_equity = self.env["product.product"].create(
            {
                "name": "Not Investment test product",
                "is_equity": False,
                "list_price": 60.0,
            }
        )

        equity_invoice_line = self.env["account.invoice.line"].create(
            {
                "name": "Test investment invoice line",
                "account_id": account.id,
                "product_id": equity.id,
                "quantity": 1,
                "price_unit": 60,
            }
        )
        not_equity_invoice_line = self.env["account.invoice.line"].create(
            {
                "name": "Test not investment invoice line",
                "account_id": account.id,
                "product_id": not_equity.id,
                "quantity": 1,
                "price_unit": 60,
            }
        )

        equity_invoice = self.env["account.invoice"].create(
            {
                "partner_id": self.partner_1.id,
            }
        )
        not_equity_invoice = self.env["account.invoice"].create(
            {
                "partner_id": self.partner_1.id,
            }
        )
        equity_invoice.invoice_line_ids |= equity_invoice_line
        equity_invoice.stage = "paid"

        not_equity_invoice.invoice_line_ids |= not_equity_invoice_line
        not_equity_invoice.stage = "paid"

        equity_old_price = equity_invoice_line.price_unit
        not_equity_old_price = not_equity_invoice_line.price_unit

        multiplier = 10

        equity_invoice._multiply_investments(multiplier)
        not_equity_invoice._multiply_investments(multiplier)

        self.assertEqual(
            equity_invoice.invoice_line_ids.price_unit,
            equity_old_price * multiplier,
        )
        self.assertEqual(
            equity_invoice.payment_term_id,
            self.env.ref("commown.investment_payment_term"),
        )
        self.assertEqual(
            not_equity_invoice.invoice_line_ids.price_unit,
            not_equity_old_price,
        )
