from odoo import _, api, models

from odoo.addons.account_payment_slimpay.models.payment import SlimpayTransaction


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


class CommownSlimpayTransaction(models.Model):
    _inherit = "payment.transaction"

    @api.multi
    def slimpay_s2s_do_transaction(self, **kwargs):
        "Execute non-interactive slimpay transactions in a job queue"
        if self.env.context.get("slimpay_async_http", False):
            self.with_delay(max_retries=1)._slimpay_s2s_do_transaction(**kwargs)
            return True
        else:
            return super().slimpay_s2s_do_transaction(**kwargs)

    def _slimpay_s2s_do_transaction(self, **kwargs):
        "Slimpay transaction: MUST be executed in a queue job"
        result = SlimpayTransaction.slimpay_s2s_do_transaction(self, **kwargs)
        if not result:
            raise ValueError(_("Slimpay transaction failed!"))
