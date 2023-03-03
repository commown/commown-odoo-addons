from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    uniquify_token = fields.Boolean(
        string="Uniquify payment token?",
        default=False,
        help=(
            "If set, when a partner below this one in the hierarchy is"
            " associated with previous tokens, its token become obsolete."
        ),
    )

    def get_obsolete_tokens(self, newer_token):
        """Return the obsolete tokens of current partner

        Go up the partner hierarchy (including current) until we find
        a partner with uniquify_token set to true, if any, and return
        the payment token of its children (including itself).

        Return an empty payment.token instance if none where found.
        """

        self.ensure_one()

        if self.uniquify_token:
            return self.env["payment.token"].search(
                [
                    ("partner_id", "child_of", self.id),
                    ("id", "!=", newer_token.id),
                ]
            )

        elif self.parent_id:
            return self.parent_id.get_obsolete_tokens(newer_token)

        return self.env["payment.token"]
