from odoo import models


class PaymentAcquirerSlimpay(models.Model):
    _inherit = "payment.acquirer"

    def _slimpay_tx_completed(self, tx, order_doc, **tx_attrs):
        "Use last slimpay transaction token as partner payment_token_id"
        token = super(PaymentAcquirerSlimpay, self)._slimpay_tx_completed(
            tx, order_doc, **tx_attrs
        )
        tx.mapped("sale_order_ids.partner_id").update(
            {
                "payment_token_id": token.id,
            }
        )
        return token
