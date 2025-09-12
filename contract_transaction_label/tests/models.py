from odoo import fields, models


class TestAccountMove(models.Model):
    _inherit = "account.move"

    # Test field to place the context variable
    # `payment_transaction_label` for tests checks
    received_label = fields.Text()


class TestPaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    def _send_payment_request(self):
        self.invoice_ids.write(
            {"received_label": self.env.context.get("payment_transaction_label", False)}
        )
        return super()._send_payment_request()
