from odoo import fields, models


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    obsolescence_action_ids = fields.Many2many(
        "payment_token_uniquify.obsolescence_action",
        string="Payment token obsolescence actions",
    )

    def run_obsolete_token_actions(self, new_token):
        self.ensure_one()
        obsolete_tokens = new_token.partner_id.get_obsolete_tokens(new_token)
        if obsolete_tokens:
            self.obsolescence_action_ids.run(obsolete_tokens, new_token)
