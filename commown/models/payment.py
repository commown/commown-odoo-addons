from odoo import models


class PaymentAcquirerSlimpay(models.Model):
    _inherit = ["payment.acquirer", "server.env.mixin"]
    _name = "payment.acquirer"

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

    @property
    def _server_env_fields(self):
        base_fields = super()._server_env_fields
        payment_fields = {
            "slimpay_api_url": {},
            "slimpay_creditor": {},
            "slimpay_app_id": {},
            "slimpay_app_secret": {},
        }
        payment_fields.update(base_fields)
        return payment_fields
