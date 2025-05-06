import json

from coreapi.exceptions import ErrorMessage
from mock import patch
from odoo_test_helper import FakeModelLoader

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.account_payment_slimpay.models.slimpay_utils import SlimpayClient


@tagged("-at_install", "post_install")
class SlimpayPaymentTC(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.loader = FakeModelLoader(cls.env, cls.__module__)
        cls.loader.backup_registry()
        from .models import TestPaymentProvider, TestPaymentTransaction

        cls.loader.update_registry((TestPaymentTransaction, TestPaymentProvider))

    @classmethod
    def tearDownClass(cls):
        cls.loader.restore_registry()
        super().tearDownClass()

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

    def test_support(self):
        slimpay = self.env.ref("account_payment_slimpay.payment_provider_slimpay")
        self.assertEqual(slimpay.support_refund, "partial")
        self.assertTrue(slimpay.support_tokenization)

    def test_send_payment_request_ok(self):
        def fake_action(method, func, params=None):
            """Fake code for slimpay client `action` method

            Checks the params common to all calls and return a result
            depending on the arguments to check easily.
            """

            if method == "GET" and func == "get-mandates":
                self.assertEqual(params["id"], self.token.provider_ref)
                return {"reference": "MANDATE_REF"}

            elif method == "POST" and func in (
                "create-payins",
                "create-payouts",
            ):  # pragma: no cover
                self.assertEqual(params["mandate"]["reference"], "MANDATE_REF")
                self.assertEqual(params["amount"], 149.2)  # rounded amount
                params["func"] = func
                return {
                    "executionStatus": "toprocess",
                    "state": "accepted",
                    "reference": json.dumps(params),
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
            payment_in.with_context(slimpay_payin_label="my payin label").action_post()
            payment_out.action_post()

        tx_in = payment_in.payment_transaction_id
        self.assertEqual(tx_in.state, "done")
        slimpay_call_params = json.loads(tx_in.provider_reference)
        self.assertEqual(slimpay_call_params["func"], "create-payins")
        self.assertEqual(slimpay_call_params["label"], "my payin label")
        self.assertEqual(slimpay_call_params["amount"], 149.2)
        self.assertEqual(slimpay_call_params["currency"], "EUR")

        tx_out = payment_out.payment_transaction_id
        self.assertEqual(tx_out.state, "done")
        slimpay_call_params = json.loads(tx_out.provider_reference)
        self.assertEqual(slimpay_call_params["func"], "create-payouts")
        self.assertEqual(slimpay_call_params["label"], "test payment")
        self.assertEqual(slimpay_call_params["amount"], 149.2)
        self.assertEqual(slimpay_call_params["currency"], "EUR")

        # Test coverage: notify an already done transaction:
        chan = "odoo.addons.account_payment_slimpay.models.payment_transaction"
        with self.assertLogs(chan, level="DEBUG") as cm:
            tx_in._process_notification_data({})
        self.assertIn(
            "DEBUG:%s:Transaction '%s' is already completed!" % (chan, tx_in.reference),
            cm.output,
        )

    def test_transaction_notification_methods(self):
        tx_model = self.env["payment.transaction"]

        txs = tx_model._get_tx_from_notification_data("dummy-code", {})
        self.assertFalse(txs.filtered(lambda tx: tx.provider_id.code == "slimpay"))

        # Our `_process_notification_data` override should not crash and call the
        # super() chain to apply demo provider's transaction behaviour:
        provider = self.env["payment.provider"].create({"code": "test", "name": "Test"})
        tx = tx_model.create(
            {
                "provider_id": provider.id,
                "provider_reference": "my-ref",
                "amount": 20.0,
                "currency_id": self.env.ref("base.EUR").id,
                "partner_id": self.partner.id,
            }
        )
        self.assertEqual(tx.state, "draft")
        tx._process_notification_data({"simulated_state": "pending"})
        self.assertEqual(tx.state, "pending")

        self.assertEqual(tx._label(), tx.reference)
        tx.reference = False
        self.assertEqual(tx._label(), "TR%d" % tx.id)

    def test_send_payment_request_error(self):
        meth_in = self.env.ref("account.account_payment_method_manual_in")
        payment = self._create_payment(
            payment_type="inbound", payment_method_id=meth_in.id
        )
        with patch.object(
            SlimpayClient, "create_payment", side_effect=ErrorMessage("crash")
        ):
            payment.action_post()

        tx = payment.payment_transaction_id
        self.assertEqual(tx.state, "error")
        self.assertEqual(tx.state_message, "crash")
