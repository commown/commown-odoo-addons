from odoo import fields

from odoo.addons.payment_token_uniquify.tests.common import PaymentTokenUniquifyTC


def _payment_prefs(interval, rule_type, next_date):
    return {
        "invoice_merge_recurring_interval": interval,
        "invoice_merge_recurring_rule_type": rule_type,
        "invoice_merge_next_date": next_date and fields.Date.to_date(next_date),
    }


class PaymentTokenTC(PaymentTokenUniquifyTC):
    def setUp(self):
        """Setup test data: two partners of self.company_s1 have a token
        and a contract using it:

          * first token is the main one of the contract's partner
          * second token is directly linked to the contract
        """
        super().setUp()

        token1 = self.new_payment_token(self.company_s1_w1)
        self.contract1 = self.new_contract(self.company_s1_w1)
        self.company_s1_w1.payment_token_id = token1.id

        token2 = self.new_payment_token(self.company_s1_w2, set_as_partner_token=False)
        self.contract2 = self.new_contract(self.company_s1_w2)
        self.contract2.payment_token_id = token2.id

    def new_contract(self, partner):
        product = self.env.ref("product.product_product_1")
        return self.env["contract.contract"].create(
            {
                "name": "Test Contract",
                "partner_id": partner.id,
                "invoice_partner_id": partner.id,
                "pricelist_id": partner.property_product_pricelist.id,
                "contract_type": "sale",
                "contract_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "name": "Services from #START# to #END#",
                            "quantity": 1,
                            "uom_id": product.uom_id.id,
                            "price_unit": 100,
                            "recurring_rule_type": "monthly",
                            "recurring_interval": 1,
                            "date_start": "2018-02-15",
                            "recurring_next_date": "2018-02-15",
                        },
                    )
                ],
            }
        )

    def check_payment_prefs(self, partner, expected_prefs):
        self.assertEqual({f: partner[f] for f in expected_prefs}, expected_prefs)

    def test_copy_invoice_partner(self):
        old_inv_partner = self.company_s1_w1.copy(
            {"type": "invoice", "parent_id": self.company_s1_w1.id}
        )

        new_token = self._trigger_obsolescence("copy_invoice_partner")

        new_inv_partner = new_token.partner_id.mapped("child_ids")
        self.assertEqual(new_inv_partner.type, "invoice")
        self.assertEqual(new_inv_partner.payment_token_id, new_token)

        self.assertFalse(old_inv_partner.active)
        self.assertTrue(new_inv_partner.active)

    def test_reset_payment_token(self):
        "Check that obsolete token deactivation also resets partner payment prefs"

        # Check or enforce test prerequisites
        self.assertFalse(self.company_s1.isolated_payment_tokens)
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
        # Configure acquirer with invoice partner copy and contract reattribution
        # then trigger obsolescence:
        self.company_s1_w1.copy({"type": "invoice", "parent_id": self.company_s1_w1.id})
        new_token = self._trigger_obsolescence(
            "copy_invoice_partner",
            "reattribute_contracts",
        )

        # Check the results: the new partner has replaced the old ones as
        # contract partners; the (optional) contracts token has been removed
        # so that the new token is always used for contract automatic payment:
        p_inv = new_token.partner_id.child_ids
        self.assertEqual(p_inv.type, "invoice")
        self.assertEqual(p_inv.payment_token_id, new_token)
        self.assertEqual(self.contract1.partner_id, new_token.partner_id)
        self.assertEqual(self.contract1.invoice_partner_id, p_inv)
        self.assertFalse(self.contract1.payment_token_id)

        self.assertEqual(self.contract2.partner_id, new_token.partner_id)
        self.assertEqual(self.contract2.invoice_partner_id, p_inv)
        self.assertFalse(self.contract2.payment_token_id)

    def test_action_reattribute_draft_contract_invoices(self):
        # Generate draft invoices (contract isauto_pay is False)
        inv = self.contract1._recurring_create_invoice()

        # Configure acquirer with invoice partner copy and draft invoices reattribution
        # then trigger obsolescence:
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
        self.company_s1_w1.update(_payment_prefs(2, "monthly", "2018-02-19"))
        self.company_s1_w2.update(_payment_prefs(1, "yearly", "2018-02-28"))

        # Configure acquirer with invoice merge prefs set and trigger obsolescence:
        new_token = self._trigger_obsolescence("set_partner_invoice_merge_prefs")

        # Check the results: payment prefs must have been smartly set on new partner
        self.check_payment_prefs(
            new_token.partner_id, _payment_prefs(2, "monthly", "2018-02-28")
        )

    def test_action_set_partner_invoice_merge_prefs_2(self):
        "Do not change a partner's payment prefs on new mandate signature"
        self.company_s1_w1.update(_payment_prefs(2, "monthly", "2018-02-19"))
        self.company_s1_w2.update(_payment_prefs(1, "yearly", "2018-02-28"))

        # Configure acquirer with invoice merge prefs setting, preset the new
        # partner's payment preferences and trigger obsolescence
        payment_prefs = _payment_prefs(1, "monthly", "2018-02-03")
        new_token = self._trigger_obsolescence(
            "set_partner_invoice_merge_prefs",
            **payment_prefs,
        )

        # Check the results: payment prefs of the new signee must be untouched
        self.check_payment_prefs(new_token.partner_id, payment_prefs)
