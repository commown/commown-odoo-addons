from odoo import api, models


class PaymentToken(models.Model):
    _inherit = "payment.token"

    @api.model_create_multi
    def create(self, vals_list):
        tokens = super().create(vals_list)
        for token in tokens:
            token.provider_id.with_delay(max_retries=1).run_obsolete_token_actions(
                token
            )
        return tokens
