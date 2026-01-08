from contextlib import contextmanager
from unittest.mock import patch

from odoo_test_helper import FakeModelLoader

from odoo.addons.contract.tests.test_contract import TestContractBase
from odoo.addons.queue_job.tests.common import trap_jobs


class TestContract(TestContractBase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Use contract_payment_auto payment transaction test class
        cls.loader = FakeModelLoader(cls.env, cls.__module__)
        cls.loader.backup_registry()
        from odoo.addons.contract_payment_auto.tests.models import TransactionTest

        from .base import TestTargetStateContextBase

        cls.loader.update_registry((TransactionTest, TestTargetStateContextBase))

        # Configure invoice creation in jobs and contract automatic payment:
        cls.env["ir.config_parameter"].sudo().set_param("contract.queue.job", "True")
        cls.contract.is_auto_pay = True

        cls.provider = cls.env["payment.provider"].create(
            {
                "name": "Dummy Provider",
                "code": "none",
                "state": "test",
                "is_published": True,
                "allow_tokenization": True,
                "company_id": cls.env.company.id,
            }
        )

        journal = cls.env["account.journal"].search(
            [("type", "=", "bank"), ("company_id", "=", cls.env.company.id)],
            limit=1,
        )

        with cls.mocked_get_payment_method_information(cls):
            cls.provider_method = cls.env["account.payment.method"].create(
                {"name": "Dummy method", "code": "none", "payment_type": "inbound"}
            )
            cls.provider.journal_id = journal.id

        cls.contract.payment_token_id = cls.env["payment.token"].create(
            {
                "payment_details": "Test Token",
                "partner_id": cls.partner.id,
                "active": True,
                "provider_id": cls.provider.id,
                "provider_ref": "Test",
            }
        )

    @classmethod
    def tearDownClass(cls):
        cls.loader.restore_registry()
        super().tearDownClass()

    @contextmanager
    def mocked_get_payment_method_information(self):
        orig_meth = self.env["account.payment.method"]._get_payment_method_information

        def _get_payment_method_information(*args, **kwargs):
            res = orig_meth()
            res["none"] = {"mode": "electronic", "domain": [("type", "=", "bank")]}
            return res

        with patch.object(
            self.env.registry["account.payment.method"],
            "_get_payment_method_information",
            _get_payment_method_information,
        ):
            yield

    def test_finalize_in_job_ok(self):
        contracts = self.contract | self.contract2

        with trap_jobs() as trap:
            contracts.with_context(test_target_state="done").recurring_create_invoice()

        trap.assert_jobs_count(2)
        trap.perform_enqueued_jobs()

        inv = self.env["account.move"].search(
            [("line_ids.contract_line_id.contract_id", "=", self.contract.id)]
        )
        self.assertEqual(inv.state, "posted")
        self.assertEqual(inv.payment_state, "paid")

        self.assertEqual(inv.mapped("transaction_ids.state"), ["done"])
        self.assertEqual(inv.mapped("transaction_ids.payment_id.state"), ["posted"])

    def test_finalize_in_job_error(self):
        contracts = self.contract | self.contract2

        with trap_jobs() as trap:
            contracts.with_context(test_target_state="error").recurring_create_invoice()

        trap.assert_jobs_count(2)
        trap.perform_enqueued_jobs()

        inv = self.env["account.move"].search(
            [("line_ids.contract_line_id.contract_id", "=", self.contract.id)]
        )
        self.assertEqual(inv.state, "posted")
        self.assertEqual(inv.payment_state, "not_paid")
        self.assertEqual(inv.mapped("transaction_ids.state"), ["error"])
        self.assertFalse(inv.mapped("transaction_ids.payment_id"))
