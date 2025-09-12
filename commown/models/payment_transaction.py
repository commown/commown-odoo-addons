from odoo import models


class SlimpayTransaction(models.Model):
    _inherit = "payment.transaction"

    def _slimpay_tx_completed(self, client, order_doc, **tx_attrs):
        "Use last slimpay transaction token as partner payment_token_id"
        token = super()._slimpay_tx_completed(client, order_doc, **tx_attrs)
        self.mapped("sale_order_ids.partner_id").update({"payment_token_id": token.id})
        return token
