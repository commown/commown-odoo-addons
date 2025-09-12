from dateutil.relativedelta import relativedelta
from odoo_test_helper import FakeModelLoader

from odoo.addons.contract.tests.test_contract import TestContractBase


class ContractPaymentTC(TestContractBase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.loader = FakeModelLoader(cls.env, cls.__module__)
        cls.loader.backup_registry()
        from .models import TestAccountMove, TestPaymentTransaction

        cls.loader.update_registry((TestAccountMove, TestPaymentTransaction))

        provider = cls.env.ref("payment.payment_provider_stripe")
        provider.state = "test"
        payment_token = cls.env["payment.token"].create(
            {
                "payment_details": "Test Provider Token",
                "partner_id": cls.contract.partner_id.id,
                "provider_id": provider.id,
                "provider_ref": "Provider mandate ref",
            }
        )
        cls.contract.is_auto_pay = True
        cls.contract.partner_id.payment_token_id = payment_token

    @classmethod
    def tearDownClass(cls):
        cls.loader.restore_registry()
        super().tearDownClass()

    def test_default_payin_label(self):
        "Base transaction_label value is #INV#, and the computed label should reflect that."
        invoice = self.contract.recurring_create_invoice()
        self.assertEqual(invoice.received_label, invoice.name)

    def test_custom_payin_label(self):
        # Make this the last invoice of the contract
        # (see project task #15112: crash on last invoice generation)
        for cline in self.contract.contract_line_ids:
            cline.date_start = cline.recurring_next_date
            cline.date_end = cline.next_period_date_end - relativedelta(days=1)

        self.contract.transaction_label = "Invoice #START# - #END# (#INV#)"
        invoice = self.contract.recurring_create_invoice()

        expected_label = "Invoice 01/15/2018 - 02/13/2018 (%s)" % invoice.name

        self.assertEqual(invoice.received_label, expected_label)

    def test_no_contract_label(self):
        """
        Contracts w/out transaction_label should not interfere
        with the base behavior.
        (Mainly for coverage purposes)
        """
        self.contract.transaction_label = False
        payment_transaction_label = "Test label"

        invoice = self.contract.with_context(
            payment_transaction_label=payment_transaction_label
        ).recurring_create_invoice()
        self.assertEqual(invoice.received_label, payment_transaction_label)
