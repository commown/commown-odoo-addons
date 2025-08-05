from unittest.mock import patch

from dateutil.relativedelta import relativedelta

from odoo.addons.contract.tests.test_contract import TestContractBase


class ContractPaymentTC(TestContractBase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        slimpay = cls.env.ref("account_payment_slimpay.payment_provider_slimpay")
        slimpay.state = "test"
        payment_token = cls.env["payment.token"].create(
            {
                "payment_details": "Test Slimpay Token",
                "partner_id": cls.contract.partner_id.id,
                "provider_id": slimpay.id,
                "provider_ref": "Slimpay mandate ref",
            }
        )
        cls.contract.is_auto_pay = True
        cls.contract.partner_id.payment_token_id = payment_token

    def setUp(self):
        super().setUp()
        client_patcher = patch(
            "odoo.addons.account_payment_slimpay.models.slimpay_utils.get_client"
        )
        client_patcher.start()
        self.addCleanup(client_patcher.stop)

    def test_default_payin_label(self):
        with patch(
            "odoo.addons.account_payment_slimpay.models."
            "slimpay_utils.SlimpayClient.create_payment"
        ) as pay:
            invoice = self.contract.recurring_create_invoice()
            label = pay.call_args[0][-1]
            self.assertEqual(label, invoice.name)

    def test_custom_payin_label(self):
        # Make this the last invoice of the contract
        # (see project task #15112: crash on last invoice generation)
        for cline in self.contract.contract_line_ids:
            cline.date_start = cline.recurring_next_date
            cline.date_end = cline.next_period_date_end - relativedelta(days=1)

        self.contract.write(
            {
                "transaction_label": "Invoice #START# - #END# (#INV#)",
            }
        )
        with patch(
            "odoo.addons.account_payment_slimpay.models."
            "slimpay_utils.SlimpayClient.create_payment"
        ) as pay:
            invoice = self.contract.recurring_create_invoice()
            label = pay.call_args[0][-1]
            expected_label = "Invoice 01/15/2018 - 02/13/2018 (%s)" % invoice.name
            self.assertEqual(label, expected_label)
