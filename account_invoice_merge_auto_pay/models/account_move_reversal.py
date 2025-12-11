from odoo import models


class AccountMoveReversal(models.TransientModel):
    _inherit = "account.move.reversal"

    def _prepare_default_reversal(self, move):
        res = super()._prepare_default_reversal(move)
        res.update({"auto_merge": False})
        return res
