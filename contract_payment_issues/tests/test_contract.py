from odoo.addons.contract.tests.test_contract import TestContractBase


class PaymentIssuesContractTC(TestContractBase):
    def test_contract_payment_issues(self):
        # Setup
        inv = self.contract._recurring_create_invoice()
        payment_issue_task = self.env["project.task"].create(
            {"name": "Test task", "invoice_id": inv.id}
        )

        # Force a recomputation
        self.contract.invalidate_recordset()
        self.assertIn(payment_issue_task, self.contract.payment_issue_ids)
