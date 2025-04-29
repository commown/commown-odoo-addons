from mock import patch

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.account_payment_slimpay.models.payment import SlimpayClient


@tagged("-at_install", "post_install")
class SlimpayPaymentTC(TransactionCase):
    def setUp(self):
        patcher = patch(
            "odoo.addons.account_payment_slimpay.models." "slimpay_utils.get_client"
        )
        patcher.start()
        super().setUp()
        self.addCleanup(patcher.stop)

        self.partner = self.env.ref("base.res_partner_2")

        slimpay = self.env.ref("account_payment_slimpay.payment_provider_slimpay")
        slimpay.state = "enabled"

        self.token = self.env["payment.token"].create(
            {
                "partner_id": self.partner.id,
                "provider_id": slimpay.id,
                "provider_ref": "Slimpay mandate ref",
            }
        )

        self.journal = (
            self.env["account.journal"]
            .search([("type", "=", "bank")], limit=1)
            .ensure_one()
        )

    def _create_payment(self, **kwargs):
        data = {
            "amount": 149.20000000000002,
            "payment_token_id": self.token.id,
            "partner_id": self.partner.id,
            "partner_type": "customer",
            "journal_id": self.journal.id,
            "ref": "test payment",
        }
        data.update(kwargs)
        return self.env["account.payment"].create(data)

    def test_send_payment_request(self):
        def fake_action(method, func, params=None):
            """Fake code for slimpay client `action` method

            Checks the params common to all calls and return a result
            depending on the arguments to check easily.
            """

            if method == "GET" and func == "get-mandates":
                self.assertEqual(params["id"], self.token.provider_ref)
                return {"reference": "MANDATE_REF"}

            elif method == "POST" and func in ("create-payins", "create-payouts"):
                self.assertEqual(params["mandate"]["reference"], "MANDATE_REF")
                self.assertEqual(params["amount"], 149.2)  # rounded amount
                return {
                    "executionStatus": "toprocess",
                    "state": "accepted",
                    "reference": func + "-REF",
                }  # easy check of called meth

        meth_in = self.env.ref("account.account_payment_method_manual_in")
        payment_in = self._create_payment(
            payment_type="inbound", payment_method_id=meth_in.id
        )

        meth_out = self.env.ref("account.account_payment_method_manual_out")

        payment_out = self._create_payment(
            payment_type="outbound", payment_method_id=meth_out.id
        )

        with patch.object(SlimpayClient, "action", side_effect=fake_action):
            payment_in.action_post()
            payment_out.action_post()

        tx_in = payment_in.payment_transaction_id
        self.assertEqual(tx_in.state, "done")
        self.assertEqual(tx_in.provider_reference, "create-payins-REF")

        tx_out = payment_out.payment_transaction_id
        self.assertEqual(tx_out.state, "done")
        self.assertEqual(tx_out.provider_reference, "create-payouts-REF")
