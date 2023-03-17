import logging

from odoo import api, fields, models

_logger = logging.getLogger(__file__)


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
            _logger.debug(
                "Running obsolete token action %s with obsolete tokens %s and new %s"
                % (action.name, obsolete_tokens.ids, new_token.id)
            )
            meth_name = "_run_action_" + action.technical_name
            getattr(self, meth_name)(obsolete_tokens, new_token)

    @api.model
    def _run_action_deactivate(self, obsolete_tokens, new_token):
        "Set the token active field to False"
        obsolete_tokens.update({"active": False})

        # 2 cases here:
        # - the partner's token has been replaced by the new one
        #   (e.g. a single user changes is own token)
        # - the partner's token is now obsolete: remove it to show
        #   web UI users that the partner has no usable token anymore
        for partner in obsolete_tokens.mapped("partner_id"):
            if partner.payment_token_id in obsolete_tokens:
                partner.payment_token_id = False
