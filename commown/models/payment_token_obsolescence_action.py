from datetime import date

from odoo import api, fields, models


class PaymentTokenUniquifyObsolescenceAction(models.Model):
    _inherit = "payment_token_uniquify.obsolescence_action"

    technical_name = fields.Selection(
        selection_add=[
            ("copy_invoice_partner", "Copy invoice partner"),
            ("reattribute_contracts", "Reattribute contracts"),
            (
                "reattribute_draft_contract_invoices",
                "Reattribute draft contract invoices",
            ),
            (
                "set_partner_invoice_merge_prefs",
                "Set partner invoice merge preferences",
            ),
        ],
    )

    @api.model
    def _run_action_copy_invoice_partner(self, obsolete_tokens, new_token):
        """Copy the first invoice partner of the partners of the obsolete tokens.
        The new invoice partner is added as a child of the new token partner.
        """
        children = obsolete_tokens.mapped("partner_id.child_ids")
        for p_inv in children.filtered(lambda p: p.type == "invoice"):
            p_inv.copy({"parent_id": new_token.partner_id.id})
            p_inv.active = False
            break

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
                "invoice_partner_id": partner.address_get(["invoice"])["invoice"],
            }
        )
        contracts.filtered(lambda c: c.payment_token_id in obsolete_tokens).update(
            {"payment_token_id": False}
        )

    @api.model
    def _run_action_reattribute_draft_contract_invoices(
        self, obsolete_tokens, new_token
    ):
        """Reattribute the draft invoices of partners which token just became obsolete
        to the partner of the new token.
        """

        p_inv_id = new_token.partner_id.address_get(["invoice"])["invoice"]
        self.env["account.invoice"].search(
            [
                ("type", "=", "out_invoice"),
                ("state", "=", "draft"),
                ("partner_id.payment_token_id", "in", obsolete_tokens.ids),
                ("invoice_line_ids.contract_line_id", "!=", False),
            ]
        ).update({"partner_id": p_inv_id})

    @api.model
    def _run_action_set_partner_invoice_merge_prefs(self, obsolete_tokens, new_token):
        "Set new token's partner invoice merge/ payment preferences"

        field_rtype = "invoice_merge_recurring_rule_type"
        field_rinterval = "invoice_merge_recurring_interval"
        field_date = "invoice_merge_next_date"

        # Select the partner with the most recent invoice merge date
        # (= who has the more recently used invoice merge preferences):
        partners = (obsolete_tokens | new_token).mapped("partner_id")
        max_date, max_date_partner = None, None
        for partner in partners.filtered(field_date):
            if max_date is None or max_date < partner[field_date]:
                max_date = partner[field_date]
                max_date_partner = partner

        # If no partner has an invoice merge date, return for the sake of robustness:
        if max_date is None:
            return

        # Use the more recently used invoice merge preferences with a date in the future
        rtype, rint = max_date_partner[field_rtype], max_date_partner[field_rinterval]
        new_prefs = {field_date: max_date, field_rtype: rtype, field_rinterval: rint}

        date_int = self.env["res.partner"].invoice_merge_time_interval(rtype, rint)
        while new_prefs[field_date] < fields.Date.context_today(self):
            new_prefs[field_date] += date_int

        new_token.partner_id.update(new_prefs)
