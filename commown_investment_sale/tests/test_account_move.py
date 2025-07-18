from odoo.tests import tagged, TransactionCase


@tagged("-at_install", "post_install")
class AccountInvoiceTC(TransactionCase):

    def test_multiply_investments(self):
        account = self.env["account.account"].search([("code", "=like", "2751%")])
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

        equity_invoice_line = self.env["account.move.line"].create(
            {
                "name": "Test investment invoice line",
                "account_id": account.id,
                "product_id": equity.id,
                "quantity": 1,
                "price_unit": 60,
            }
        )
        not_equity_invoice_line = self.env["account.move.line"].create(
            {
                "name": "Test not investment invoice line",
                "account_id": account.id,
                "product_id": not_equity.id,
                "quantity": 1,
                "price_unit": 60,
            }
        )

        equity_invoice = self.env["account.move"].create(
            {
                "partner_id": self.partner_1.id,
            }
        )
        not_equity_invoice = self.env["account.move"].create(
            {
                "partner_id": self.partner_1.id,
            }
        )
        equity_invoice.line_ids |= equity_invoice_line
        equity_invoice.stage = "paid"

        not_equity_invoice.line_ids |= not_equity_invoice_line
        not_equity_invoice.stage = "paid"

        equity_old_price = equity_invoice_line.price_unit
        not_equity_old_price = not_equity_invoice_line.price_unit

        multiplier = 10

        equity_invoice._multiply_investments(multiplier)
        not_equity_invoice._multiply_investments(multiplier)

        self.assertEqual(
            equity_invoice.line_ids.price_unit,
            equity_old_price * multiplier,
        )
        self.assertEqual(
            equity_invoice.payment_term_id,
            self.env.ref("commown.investment_payment_term"),
        )
        self.assertEqual(
            not_equity_invoice.line_ids.price_unit,
            not_equity_old_price,
        )
