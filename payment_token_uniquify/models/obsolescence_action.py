from odoo import api, fields, models


class PaymentTokenUniquifyObsolescenceAction(models.Model):
    _name = "payment_token_uniquify.obsolescence_action"
    _description = "Action to be taken when a payment token becomes obsolete"
    _order = "sequence asc"

    name = fields.Char(required=True)

    technical_name = fields.Selection(
        [("deactivate", "Deactivate")],
        string="Technical name",
        required=True,
    )

    sequence = fields.Integer(
        "Sequence",
        help="Action execution order (the smallest for the first executed action)",
        required=True,
        default=1,
    )

    @api.multi
    def run(self, obsolete_tokens, new_token):
        for action in self:
            meth_name = "_run_action_" + action.technical_name
            getattr(self, meth_name)(obsolete_tokens, new_token)

    @api.model
    def _run_action_deactivate(self, obsolete_tokens, new_token):
        "Set the token active field to False"
        obsolete_tokens.update({"active": False})
