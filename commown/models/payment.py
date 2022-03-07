from odoo import models


class PaymentAcquirerSlimpay(models.Model):
    _inherit = 'payment.acquirer'

    def _slimpay_tx_completed(self, tx, order_doc, **tx_attrs):
        'Use last slimpay transaction token as partner payment_token_id'
        token = super(PaymentAcquirerSlimpay, self)._slimpay_tx_completed(
            tx, order_doc, **tx_attrs)
        tx.sale_order_id.partner_id.payment_token_id = token.id
        return token
