import logging
from datetime import date

from odoo import api, models

_logger = logging.getLogger(__name__)

_PAYMENT_PREF_FIELDS = {
    "invoice_merge_next_date",
    "invoice_merge_recurring_rule_type",
    "invoice_merge_recurring_interval",
}

_PAYMENT_FIELDS = _PAYMENT_PREF_FIELDS | {"payment_token_id"}

_SYNC_CTX = "partner_payment_fields_sync"


class ResPartner(models.Model):
    _inherit = "res.partner"

    def get_obsolete_tokens(self, newer_token):
        """Override default behaviour to remove contract-specific secondary tokens

        These token are set directly on a contract and not the main one of their
        partner. They are generally used in a familly to use 2 different bank accounts
        for 2 different devices, and are thus still useful and excluded from obsoletes.

        """
        tokens = super().get_obsolete_tokens(newer_token)

        secondary_tokens = tokens.filtered(lambda t: t != t.partner_id.payment_token_id)

        contracts = self.env["contract.contract"].search(
            [
                ("payment_token_id", "in", secondary_tokens.ids),
                "|",
                ("date_end", ">=", date.today()),
                "&",
                ("date_end", "=", False),
                ("recurring_next_date", "!=", False),
            ]
        )

        still_useful_tokens = contracts.mapped("payment_token_id")

        return tokens - still_useful_tokens

    def reset_payment_token(self):
        "Force the reset on payment preferences on payment token reset"
        super().reset_payment_token()
        return self.update({f: False for f in _PAYMENT_PREF_FIELDS})

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)

        for rec in res.filtered(lambda rec: rec.type == "invoice" and rec.parent_id):
            rec.parent_id._copy_payment_fields_to_invoice_children()

        return res

    def _copy_payment_fields_to_invoice_children(self):
        self.ensure_one()

        if self._context.get(_SYNC_CTX, False):
            return

        _msg = "Syncing payment fields from partner %s (id %d) to its child %s (id %d)"
        _self = self.with_context(**{_SYNC_CTX: True})
        for p_inv in _self.child_ids.filtered(lambda p: p.type == "invoice"):
            _logger.debug(_msg, self.name, self.id, p_inv.name, p_inv.id)
            p_inv.update({f: self[f] for f in _PAYMENT_FIELDS})

    def write(self, vals):
        result = super().write(vals)

        if _PAYMENT_FIELDS.intersection(vals):
            # Sync payment fields to invoice childs:
            self._copy_payment_fields_to_invoice_children()

            # If not updating because of above sync, update parent payment fields:
            if self.type == "invoice" and not self._context.get(_SYNC_CTX, False):
                debug_msg = (
                    "Syncing payment fields from partner %s (id %d) to"
                    " its parent %s (id %d)"
                )
                p_parent = self.parent_id
                _logger.debug(debug_msg, self.name, self.id, p_parent.name, p_parent.id)
                p_parent.update({f: self[f] for f in _PAYMENT_FIELDS})

        return result
