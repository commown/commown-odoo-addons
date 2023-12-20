from odoo import models


class ResPartner(models.Model):
    _inherit = "res.partner"

    def get_obsolete_tokens(self, newer_token):
        "Return the obsolete tokens of current partner"

        self.ensure_one()

        return self.env["payment.token"].search(
            [
                ("partner_id", "child_of", self.commercial_partner_id.id),
                ("id", "!=", newer_token.id),
            ]
        )

    def reset_payment_token(self):
        "Set payment_token_id to False, making it possible to override this behaviour"
        self.update({"payment_token_id": False})
