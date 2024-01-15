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
        """Set new token's partner invoice merge/ payment preferences if not already set

        Following choices are made for the merge preferences:

        - Recurring type will be the smallest of the obsolete_tokens' partners
        - The recurring interval is the one corresponding to the chosen
          recurring type
        - Next merge date is computed as the max merge date of the
          obsoleted token partners.

        Note that most of the time there will be only one partner
        whose token has become obsolete.

        """

        field_rtype = "invoice_merge_recurring_rule_type"
        field_rinterval = "invoice_merge_recurring_interval"
        field_date = "invoice_merge_next_date"

        if new_token.partner_id[field_date]:
            return

        partners = obsolete_tokens.mapped("partner_id")

        rtypes = [
            rt[0] for rt in partners.fields_get(field_rtype)[field_rtype]["selection"]
        ]
        rtype, rinterval = (partners[0][field_rtype], partners[0][field_rinterval])

        for partner in partners:
            if rtypes.index(partner[field_rtype]) < rtypes.index(rtype):
                rtype = partner[field_rtype]
                rinterval = partner[field_rinterval]

        new_token.partner_id.update(
            {
                field_rtype: rtype,
                field_rinterval: rinterval,
                field_date: max(partners.mapped(field_date)),
            }
        )
