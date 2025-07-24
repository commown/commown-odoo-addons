import datetime

from odoo.tests.common import TransactionCase

_pay_prefs1 = {
    "invoice_merge_next_date": datetime.date(2020, 1, 1),
    "invoice_merge_recurring_rule_type": "yearly",
    "invoice_merge_recurring_interval": 1,
}

_pay_prefs2 = {
    "invoice_merge_next_date": datetime.date(2023, 2, 2),
    "invoice_merge_recurring_rule_type": "monthly",
    "invoice_merge_recurring_interval": 3,
}


class ResPartnerSimpleTC(TransactionCase):
    def _new_token(self, name, partner):
        provider = self.env.ref("payment.payment_provider_stripe")
        return self.env["payment.token"].create(
            {
                "payment_details": name,
                "provider_id": provider.id,
                "partner_id": partner.id,
                "provider_ref": name,
            }
        )

    def test_sync_payment_fields(self):
        p_model = self.env["res.partner"]

        p_contact = p_model.create({"name": "p", "type": "contact"})

        tok1 = self._new_token("tok1", p_contact)
        tok2 = self._new_token("tok2", p_contact)

        p_contact.update(dict(_pay_prefs1, payment_token_id=tok1.id))

        # Check sync on invoice partner creation
        p_inv = p_model.create({"parent_id": p_contact.id, "type": "invoice"})
        expected_prefs1 = dict(_pay_prefs1, payment_token_id=tok1)
        self.assertEqual(expected_prefs1, {f: p_inv[f] for f in expected_prefs1})

        # Check invoice partner sync on parent update
        p_contact.update(dict(_pay_prefs2, payment_token_id=tok2.id))
        expected_prefs2 = dict(_pay_prefs2, payment_token_id=tok2)
        self.assertEqual(expected_prefs2, {f: p_inv[f] for f in expected_prefs2})

        # Check parent sync on invoice partner update
        p_inv.update(dict(_pay_prefs1, payment_token_id=tok1.id))
        self.assertEqual(expected_prefs1, {f: p_contact[f] for f in expected_prefs1})
