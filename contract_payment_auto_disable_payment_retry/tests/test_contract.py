from odoo.tests.common import TransactionCase


class TestContractPaymentAutoDisableDefault(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.model = cls.env["contract.template"]

    def test_disable_default_invoice_mail_template_id(self):
        res = self.model._default_invoice_mail_template_id()
        self.assertEqual(res, False)

    def test_disable_default_pay_retry_mail_template_id(self):
        res = self.model._default_pay_retry_mail_template_id()
        self.assertEqual(res, False)

    def test_disable_default_default_pay_fail_mail_template_id(self):
        res = self.model._default_pay_fail_mail_template_id()
        self.assertEqual(res, False)

    def test_disable_default_auto_pay_retries(self):
        res = self.model._default_auto_pay_retries()
        self.assertEqual(res, 0)
