from .common import PaymentTokenUniquifyTC


class PaymentTokenTC(PaymentTokenUniquifyTC):
    def test_action_deactivate(self):
        "Obsolete tokens must become inactive when this action is used"
        # Configure provider, and trigger obsolescence when no tokens are set
        # (Mainly for coverage purposes)
        self._trigger_obsolescence(
            "payment_token_uniquify.obsolescence_action_deactivate"
        )

        # Create tokens for workers 1 and 2,
        # then sign them to trigger obsolesence :
        self.token1 = self.new_payment_token(self.company_s1_w1)
        self.token2 = self.new_payment_token(self.company_s1_w2)

        self.assertTrue(self.company_s1_w1.payment_token_id)
        self.assertTrue(self.company_s1_w2.payment_token_id)

        self._trigger_obsolescence(
            "payment_token_uniquify.obsolescence_action_deactivate"
        )

        self.assertFalse(self.token1.active)
        self.assertFalse(self.token2.active)

        self.assertFalse(self.company_s1_w1.payment_token_id)
        self.assertFalse(self.company_s1_w2.payment_token_id)
