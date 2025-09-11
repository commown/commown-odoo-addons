import json
from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.account_payment_slimpay.models.slimpay_utils import SlimpayClient
from odoo.addons.account_payment_slimpay.tests.test_payment import (
    SlimpayPaymentTestMixin,
)


@tagged("-at_install", "post_install")
class SlimpayPaymentTC(SlimpayPaymentTestMixin, TransactionCase):
    def test_context_label_overload(self):
        "When a label value is passed through the context, it should override the base value."
        # Setting up payments
        meth_in = self.env.ref("account.account_payment_method_manual_in")
        payment_in = self._create_payment(
            payment_type="inbound", payment_method_id=meth_in.id
        )

        meth_out = self.env.ref("account.account_payment_method_manual_out")

        payment_out = self._create_payment(
            payment_type="outbound", payment_method_id=meth_out.id
        )

        # Check pre-requisite
        context_label = "test label"

        self.assertNotEqual(payment_in.ref, context_label)
        self.assertNotEqual(payment_out.ref, context_label)

        # Check transaction labels
        # payment_in should have its base label overriden,
        # and payment_out shouldn't have its label overriden.
        with patch.object(SlimpayClient, "action", side_effect=self.fake_action()):
            payment_in.with_context(
                payment_transaction_label=context_label
            ).action_post()
            payment_out.action_post()

        tx_in = payment_in.payment_transaction_id
        self.assertEqual(tx_in.state, "done")
        slimpay_call_params = json.loads(tx_in.provider_reference)
        self.assertEqual(slimpay_call_params["label"], context_label)

        tx_out = payment_out.payment_transaction_id
        self.assertEqual(tx_out.state, "done")
        slimpay_call_params = json.loads(tx_out.provider_reference)
        self.assertEqual(slimpay_call_params["label"], payment_out.ref)
