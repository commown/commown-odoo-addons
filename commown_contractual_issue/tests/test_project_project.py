from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class ProjectTaskTC(TransactionCase):
    def test_check_contract_coherency(self):
        project = self.env["project.project"].create({"name": "Test"})
        self.assertFalse(project.require_contract)
        self.assertFalse(project.contractual_issues_tracking)

        with self.assertRaises(ValidationError) as error:
            project.contractual_issues_tracking = True
        self.assertEqual(
            error.exception.args[0],
            "A contract must be set on tasks to track contractual issues",
        )

        project.require_contract = True
        project.contractual_issues_tracking = True
        self.assertTrue(project.contractual_issues_tracking)
