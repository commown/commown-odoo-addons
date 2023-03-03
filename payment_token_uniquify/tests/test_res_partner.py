from .common import PaymentTokenUniquifyTC


class PartnerTC(PaymentTokenUniquifyTC):
    def test_get_obsolete_tokens_individuals_no_uniquify(self):
        "If uniquify_token is False on an individual, its tokens never become obsolete"

        p1 = self.env["res.partner"].create({"name": "test", "uniquify_token": False})
        t1 = self.new_payment_token(p1)
        self.new_payment_token(p1)
        self.assertFalse(p1.get_obsolete_tokens(t1))

    def test_get_obsolete_tokens_individuals_uniquify(self):
        "If uniquify_token is True on an individual, its tokens become obsolete"

        p1 = self.env["res.partner"].create({"name": "test", "uniquify_token": True})
        t1 = self.new_payment_token(p1)
        t2 = self.new_payment_token(p1)
        self.assertEqual(p1.get_obsolete_tokens(t2), t1)
        t3 = self.new_payment_token(p1)
        self.assertEqual(p1.get_obsolete_tokens(t3), t1 + t2)

    def test_get_obsolete_tokens_subcompanies_with_uniquify(self):
        "Obsolete tokens do not propagate to uniquify_token False entities"

        # Test pre-requisite:
        self.assertEqual(self.company_s1_w1.commercial_partner_id, self.company_s1)

        # Check expected behaviour:
        t11 = self.new_payment_token(self.company_s1_w1)
        self.assertFalse(self.company_s1_w1.get_obsolete_tokens(t11))
        self.assertFalse(self.company_s1_w2.get_obsolete_tokens(t11))
        t12 = self.new_payment_token(self.company_s1_w1)
        self.assertEqual(self.company_s1_w1.get_obsolete_tokens(t12), t11)
        self.assertEqual(self.company_s1_w2.get_obsolete_tokens(t12), t11)

        # New token signed by another partner in the same sub-company with uniquify:
        # previous tokens must be obsolete
        t13 = self.new_payment_token(self.company_s1_w2)
        self.assertEqual(self.company_s1_w1.get_obsolete_tokens(t13), t11 + t12)
        self.assertEqual(self.company_s1_w2.get_obsolete_tokens(t13), t11 + t12)

        # New token in another subcompany with uniquify: mustn't obsolete previous ones:
        t21 = self.new_payment_token(self.company_s2_w1)
        self.assertFalse(self.company_s2_w1.get_obsolete_tokens(t21))

        t22 = self.new_payment_token(self.company_s2_w1)
        self.assertEqual(self.company_s2_w1.get_obsolete_tokens(t22), t21)
        self.assertEqual(self.company_s2_w1.get_obsolete_tokens(t22), t21)
