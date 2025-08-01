from odoo.addons.commown_payment_token_uniquify.tests.common import (
    ContractRelatedPaymentTokenUniquifyTC,
)


class ResPartnerInvoiceActionTC(ContractRelatedPaymentTokenUniquifyTC):
    def test_action(self):
        "Action must reattribute contracts and draft invoices"
        partner = self.company_s1_w1
        inv_partner = partner.copy({"type": "invoice", "parent_id": partner.id})
        draft_inv = self.contract1._recurring_create_invoice()

        inv_partner.action_set_as_invoice_recipient()

        self.assertEqual(self.contract1.invoice_partner_id, inv_partner)
        self.assertEqual(draft_inv.partner_id, inv_partner)
