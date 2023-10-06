from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    isolated_payment_tokens = fields.Boolean(
        string="Isolate payment tokens?",
        default=False,
        help=(
            "If set, the payment token unification algorithm will stop"
            " going up the partner hierarchy to select tokens to unify."
        ),
    )

    def get_obsolete_tokens(self, newer_token):
        "Return the obsolete tokens of current partner"

        self.ensure_one()

        if self.isolated_payment_tokens:
            return self.env["payment.token"]

        if self.parent_id and not self.parent_id.isolated_payment_tokens:
            return self.parent_id.get_obsolete_tokens(newer_token)
        else:
            return self.env["payment.token"].search(
                [
                    ("partner_id", "child_of", self.id),
                    ("id", "!=", newer_token.id),
                ]
            )

    def reset_payment_token(self):
        "Set payment_token_id to False, making it possible to override this behaviour"
        self.update({"payment_token_id": False})
