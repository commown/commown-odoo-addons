from freezegun import freeze_time

from odoo import fields

from .common import ContractRelatedPaymentTokenUniquifyTC


def _payment_prefs(interval, rule_type, next_date):
    return {
        "invoice_merge_recurring_interval": interval,
        "invoice_merge_recurring_rule_type": rule_type,
        "invoice_merge_next_date": next_date and fields.Date.to_date(next_date),
    }


class PaymentTokenTC(ContractRelatedPaymentTokenUniquifyTC):
    def check_payment_prefs(self, partner, expected_prefs):
        self.assertEqual({f: partner[f] for f in expected_prefs}, expected_prefs)

    def _trigger_obsolescence(self, *_action_refs, **new_partner_kwargs):
        action_refs = tuple(
            action_ref
            if "." in action_ref
            else "commown_payment_token_uniquify.obsolescence_action_" + action_ref
            for action_ref in _action_refs
        )
        return super()._trigger_obsolescence(*action_refs, **new_partner_kwargs)

    def test_copy_invoice_partner(self):
        old_inv_partner = self.company_s1_w1.copy(
            {"type": "invoice", "parent_id": self.company_s1_w1.id}
        )

        new_token = self._trigger_obsolescence("copy_invoice_partner")

        new_inv_partner = new_token.partner_id.mapped("child_ids")
        self.assertEqual(new_inv_partner.type, "invoice")
        self.assertEqual(new_inv_partner.payment_token_id, new_token)
        self.assertEqual(new_inv_partner.name, old_inv_partner.name)

        self.assertFalse(old_inv_partner.active)
        self.assertTrue(new_inv_partner.active)

    def test_reset_payment_token(self):
        "Check that obsolete token deactivation also resets partner payment prefs"

        # Check or enforce test prerequisites
        self.assertTrue(self.company_s1_w1.payment_token_id)
        self.assertFalse(self.company_s1_w2.payment_token_id)  # Set on self.contract2

        self.company_s1_w1.update(_payment_prefs(1, "monthly", "2018-02-19"))
        self.company_s1_w2.update(_payment_prefs(1, "monthly", "2018-01-05"))

        # Trigger the tested code
        action_ref = "payment_token_uniquify.obsolescence_action_deactivate"
        self._trigger_obsolescence(action_ref)

        # Check the results
        self.check_payment_prefs(self.company_s1_w1, _payment_prefs(0, False, False))

        self.check_payment_prefs(
            self.company_s1_w2, _payment_prefs(1, "monthly", "2018-01-05")
        )

    def test_action_reattribute_contracts(self):
        # Add an invoice-typed contact child to a contract's partner:
        initial_invoice_partner = self.company_s1_w1.copy(
            {
                "type": "invoice",
                "parent_id": self.company_s1_w1.id,
                "email": "accountant@company.com",
            }
        )

        # Simulate a new contract sale: the contract is create before the payment token
        # (which is created in a job, thus *after* the contract):
        company_s1_w3 = self.new_worker(self.company_s1, name="s1_w3")
        contract3 = self.new_contract(company_s1_w3)

        # Configure payment provider with invoice partner copy and
        # contract reattribution then trigger obsolescence:
        new_token = self._trigger_obsolescence(
            "copy_invoice_partner",
            "reattribute_contracts",
            partner=company_s1_w3,
        )

        # Check the results: the new partner has replaced the old ones as
        # contract partners; the (optional) contracts token has been removed
        # so that the new token is always used for contract automatic payment:
        p_inv = new_token.partner_id.child_ids
        self.assertNotEqual(p_inv, initial_invoice_partner)  # Check it is a copy
        self.assertEqual(p_inv.type, "invoice")
        self.assertEqual(p_inv.email, "accountant@company.com")
        self.assertEqual(p_inv.payment_token_id, new_token)
        self.assertEqual(self.contract1.partner_id, new_token.partner_id)
        self.assertEqual(self.contract1.invoice_partner_id, p_inv)
        self.assertFalse(self.contract1.payment_token_id)

        # Nothing changed on contract2 as its token has NOT become obsolete
        # (because it is a secondary and contract-specific one)
        self.assertEqual(self.contract2.partner_id, self.company_s1_w2)
        self.assertEqual(self.contract2.invoice_partner_id, self.company_s1_w2)
        self.assertTrue(self.contract2.payment_token_id)

        # Contract3 invoice partner was also updated although its partner's
        # token was not obsolete, because we want it to get the same invoice
        # partner as the others:
        self.assertEqual(contract3.invoice_partner_id, p_inv)

    def test_action_reattribute_draft_contract_invoices(self):
        # Generate draft invoices (contract isauto_pay is False)
        inv = self.contract1._recurring_create_invoice()

        # Configure payment provider with invoice partner copy and
        # draft invoices reattribution then trigger obsolescence:
        self.company_s1_w1.copy({"type": "invoice", "parent_id": self.company_s1_w1.id})
        new_token = self._trigger_obsolescence(
            "copy_invoice_partner",
            "reattribute_draft_contract_invoices",
        )

        # Check the results: invoices must have been reattributed to the new partner:
        p_inv = new_token.partner_id.child_ids
        self.assertEqual(p_inv.type, "invoice")
        self.assertEqual(p_inv.payment_token_id, new_token)
        self.assertEqual(inv.partner_id, p_inv)

    def test_action_set_partner_invoice_merge_prefs_1(self):
        # set s1_w2 token to the one of contract2 so that it can become obsolete
        # (that way it is no more a secondary token)
        self.company_s1_w2.payment_token_id = self.contract2.payment_token_id

        self.company_s1_w1.update(_payment_prefs(2, "monthly", "2018-02-28"))
        self.company_s1_w2.update(_payment_prefs(1, "yearly", "2018-02-19"))

        # Configure payment provider with invoice merge prefs set and
        # trigger obsolescence:
        with freeze_time("2018-02-10"):
            new_token = self._trigger_obsolescence("set_partner_invoice_merge_prefs")

        # Check the results: payment prefs must have been smartly set on new partner
        self.check_payment_prefs(
            new_token.partner_id, _payment_prefs(2, "monthly", "2018-02-28")
        )

    def test_action_set_partner_invoice_merge_prefs_2(self):
        "Make sure the invoice merge date is in the future"
        self.company_s1_w1.update(_payment_prefs(2, "monthly", "2018-02-28"))
        self.company_s1_w2.update(_payment_prefs(1, "yearly", "2018-02-19"))

        # Configure payment providre with invoice merge prefs setting,
        # preset the new partner's payment preferences and trigger
        # obsolescence
        partner = self.new_worker(
            self.company_s1, name="s1_w3", **_payment_prefs(1, "monthly", "2017-03-03")
        )
        with freeze_time("2018-05-01"):
            new_token = self._trigger_obsolescence(
                "set_partner_invoice_merge_prefs",
                partner=partner,
            )

        # Check the results: payment prefs of the new signee must be untouched
        self.check_payment_prefs(
            new_token.partner_id,
            _payment_prefs(2, "monthly", "2018-06-28"),
        )
