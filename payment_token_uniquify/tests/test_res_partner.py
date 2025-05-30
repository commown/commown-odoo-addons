from .common import PaymentTokenUniquifyTC


class PartnerTC(PaymentTokenUniquifyTC):
    def test_get_obsolete_tokens(self):
        "Obsolete tokens are those of the first-level company of the new token partner"

        # Test pre-requisite:
        self.assertEqual(self.company_s1_w1.commercial_partner_id, self.company_s1)

        # Check expected behaviour:
        t11 = self.new_payment_token(self.company_s1_w1)
        self.assertFalse(self.company_s1_w1.get_obsolete_tokens(t11))
        self.assertFalse(self.company_s1_w2.get_obsolete_tokens(t11))
        t12 = self.new_payment_token(self.company_s1_w1)
        self.assertEqual(self.company_s1_w1.get_obsolete_tokens(t12), t11)
        self.assertEqual(self.company_s1_w2.get_obsolete_tokens(t12), t11)

        # New token signed by another partner in the same sub-company:
        # previous tokens must be obsolete
        t13 = self.new_payment_token(self.company_s1_w2)
        self.assertEqual(self.company_s1_w1.get_obsolete_tokens(t13), t11 + t12)
        self.assertEqual(self.company_s1_w2.get_obsolete_tokens(t13), t11 + t12)

        # New token in another subcompany: mustn't obsolete previous ones:
        t21 = self.new_payment_token(self.company_s2_w1)
        self.assertFalse(self.company_s2_w1.get_obsolete_tokens(t21))

        t22 = self.new_payment_token(self.company_s2_w1)
        self.assertEqual(self.company_s2_w1.get_obsolete_tokens(t22), t21)
        self.assertEqual(self.company_s2_w1.get_obsolete_tokens(t22), t21)
