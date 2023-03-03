from odoo import api, models


class PaymentToken(models.Model):
    _inherit = "payment.token"

    @api.model
    @api.returns("self", lambda value: value.id)
    def create(self, vals):
        res = super().create(vals)
        res.acquirer_id.with_delay(max_retries=1).run_obsolete_token_actions(res)
        return res
