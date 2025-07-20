from odoo.fields import Command
from odoo.tests import TransactionCase, tagged


@tagged("-at_install", "post_install")
class AccountInvoiceTC(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env.company = cls.env.companies.filtered("chart_template_id")[0]
        cls.partner = cls.env.ref("base.partner_demo_portal")

        cls.journal = cls.env["account.journal"].create(
            {
                "name": "My journal",
                "code": "RC",
                "company_id": cls.env.company.id,
                "type": "bank",
            }
        )

    def _create_and_pay_invoice(self, product):
        invoice = self.env["account.move"].create(
            {
                "partner_id": self.partner.id,
                "move_type": "out_invoice",
                "line_ids": [
                    Command.create(
                        {
                            "name": "Test investment invoice line",
                            "product_id": product.id,
                            "quantity": 1,
                            "price_unit": 60,
                        },
                    ),
                ],
            }
        )

        invoice.action_post()
        register_payment = (
            self.env["account.payment.register"]
            .with_context(active_model="account.move", active_ids=invoice.ids)
            .create({"journal_id": self.journal.id})
        )
        register_payment._create_payments()
        self.assertEqual(invoice.payment_state, "paid")
        return invoice

    def test_multiply_investments(self):
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

        equity_invoice = self._create_and_pay_invoice(equity)
        not_equity_invoice = self._create_and_pay_invoice(not_equity)

        equity_old_price = equity_invoice.line_ids[0].price_unit
        not_equity_old_price = not_equity_invoice.line_ids[0].price_unit

        multiplier = 10

        equity_invoice._multiply_investments(multiplier)
        not_equity_invoice._multiply_investments(multiplier)

        self.assertEqual(
            equity_invoice.invoice_line_ids.price_unit,
            equity_old_price * multiplier,
        )
        self.assertEqual(
            equity_invoice.invoice_payment_term_id,
            self.env.ref("commown_investment_sale.investment_payment_term"),
        )
        self.assertEqual(
            not_equity_invoice.invoice_line_ids.price_unit,
            not_equity_old_price,
        )
