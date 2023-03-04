from datetime import date

from odoo import api, fields, models


class PaymentTokenUniquifyObsolescenceAction(models.Model):
    _inherit = "payment_token_uniquify.obsolescence_action"

    technical_name = fields.Selection(
        selection_add=[
            ("reattribute_contracts", "Reattribute contracts"),
        ],
    )

    @api.model
    def _run_action_reattribute_contracts(self, obsolete_tokens, new_token):
        """Reattribute the contracts of partners which token just became obsolete
        to the partner of the new token.
        """

        contracts = self.env["contract.contract"].search(
            [
                "|",
                ("partner_id.payment_token_id", "in", obsolete_tokens.ids),
                ("payment_token_id", "in", obsolete_tokens.ids),
                "|",
                ("date_end", ">=", date.today()),
                "&",
                ("date_end", "=", False),
                ("recurring_next_date", "!=", False),
            ]
        )
        partner = new_token.partner_id
        contracts.update(
            {
                "partner_id": partner.id,
                "invoice_partner_id": partner.id,
                "payment_token_id": False,
            }
        )
