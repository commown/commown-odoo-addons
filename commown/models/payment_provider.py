from odoo import models


class PaymentProviderSlimpay(models.Model):
    _inherit = ["payment.provider", "server.env.mixin"]
    _name = "payment.provider"

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
