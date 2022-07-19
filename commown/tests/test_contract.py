from odoo.addons.contract.tests.test_contract import TestContractBase

from mock import patch


class ContractPaymentTC(TestContractBase):
    @classmethod
    def setUpClass(cls):
        super(ContractPaymentTC, cls).setUpClass()
        slimpay = (
            cls.env["payment.acquirer"]
            .search([("provider", "=", "slimpay")])
            .ensure_one()
        )
        payment_token = cls.env["payment.token"].create(
            {
                "name": "Test Slimpay Token",
                "partner_id": cls.contract.partner_id.id,
                "acquirer_id": slimpay.id,
                "acquirer_ref": "Slimpay mandate ref",
            }
        )
        cls.contract.is_auto_pay = True
        cls.contract.partner_id.payment_token_id = payment_token

    def setUp(self):
        super(ContractPaymentTC, self).setUp()
        client_patcher = patch(
            "odoo.addons.account_payment_slimpay.models." "slimpay_utils.get_client"
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
            self.assertEqual(label, invoice.number)

    def test_custom_payin_label(self):
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
            expected_label = "Invoice 01/15/2018 - 02/14/2018 (%s)" % invoice.number
            self.assertEqual(label, expected_label)

    def test_amount(self):
        "Contract amount does not take "

        self.assertEqual(self.contract.amount(), 50.0)

        formula1 = self.env["contract.line.qty.formula"].create(
            {
                "name": "[DE] Valid",
                "code": "result = 0.2  # does not matter here",
            }
        )
        self.contract.contract_line_ids.update(
            {
                "qty_type": "variable",  # [DE] important here
                "qty_formula_id": formula1,
            }
        )

        self.assertEqual(self.contract.amount(), 50.0)

        formula2 = self.env["contract.line.qty.formula"].create(
            {
                "name": "Invalid",
                "code": "result = 0.2  # does not matter here",
            }
        )

        self.contract.contract_line_ids.update(
            {
                "qty_type": "variable",
                "qty_formula_id": formula2,
            }
        )

        self.assertEqual(self.contract.amount(), 0.0)
