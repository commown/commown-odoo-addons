from .common import PaymentTokenUniquifyTC


class PaymentTokenTC(PaymentTokenUniquifyTC):
    def setUp(self):
        super().setUp()

        self.token1 = self.new_payment_token(self.company_s1_w1)
        self.token2 = self.new_payment_token(self.company_s1_w2)

        self.acquirer = self.env.ref("payment.payment_acquirer_transfer")

    def test_action_deactivate(self):
        "Obsolete tokens must become inactive when this action is used"

        # Configure acquirer to deactivate the obsoleted tokens
        self.acquirer.obsolescence_action_ids |= self.env.ref(
            "payment_token_uniquify.obsolescence_action_deactivate"
        )

        # A new token is signed
        cm = self._check_obsolete_token_action_job()
        with cm:
            new_token = self.new_payment_token(self.company_s1_w1, self.acquirer)
            cm.gen.send(new_token)

        self.assertFalse(self.token1.active)
        self.assertFalse(self.token2.active)
