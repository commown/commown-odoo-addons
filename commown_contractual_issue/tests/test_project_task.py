from odoo.fields import Date
from odoo.tests.common import Form, TransactionCase


class ProjectTaskTC(TransactionCase):
    def setUp(self):
        super().setUp()

        self.part_no_contract = self.env["res.partner"].create(
            {"name": "Part no contract"}
        )
        self.part_with_contract = self.env["res.partner"].create(
            {"name": "Part with contract"}
        )
        self.contract = self.env["contract.contract"].create(
            {"name": "Test contract", "partner_id": self.part_with_contract.id}
        )
        self.project = self.env.ref("project.project_project_1")
        self.task = self.env["project.task"].create(
            {"name": "Test task", "project_id": self.project.id, "partner_id": False}
        )

        self.assertFalse(self.task.contract_id)
        self.assertFalse(self.task.partner_id)

    def test_set_contract(self):
        """Test that onchange methode set the contract and that the rigth contract is
        choosen by _default_contract method"""
        self.task.onchange_partner_id_set_contract()
        self.assertFalse(self.task.contract_id)

        self.task.partner_id = self.part_with_contract
        self.task.onchange_partner_id_set_contract()
        self.assertEqual(self.task.contract_id, self.contract)

        self.task.partner_id = self.part_no_contract
        self.task.onchange_partner_id_set_contract()
        self.assertFalse(self.task.contract_id)

    def test_set_partner(self):
        self.task.onchange_contract_id_set_partner()
        self.assertFalse(self.task.partner_id)

        self.task.contract_id = self.contract
        self.task.onchange_contract_id_set_partner()
        self.assertEqual(self.task.partner_id, self.part_with_contract)

        # For coverage
        self.task.partner_id = False
        self.part_with_contract.is_company = True
        self.task.onchange_contract_id_set_partner()
        self.assertFalse(self.task.partner_id)

    def test_contractual_issue_date_required_from_view(self):
        """
        When modifying a task with contractual issue tracking through the view,
        the contractual_issue_date field should be required.
        """
        self.task.contractual_issue_date = False

        # Case 1: contractual_issues_tracking is off
        self.project.contractual_issues_tracking = False

        f1 = Form(self.task)
        f1.description = "This should pass"
        f1.save()

        self.assertFalse(self.task.contractual_issue_date)

        # Case 2: contractual_issues_tracking is on
        self.task.contract_id = self.contract

        self.project.require_contract = True
        self.project.contractual_issues_tracking = True

        f2 = Form(self.task)

        # Leaving contractual_issue_date unassigned should lead to an error.
        f2.description = "This shouldn't pass"
        with self.assertRaises(AssertionError) as exc:
            f2.save()

        self.assertIn(
            "contractual_issue_date is a required field", exc.exception.args[0]
        )

        # Assigning contractual_issue_date should allow saving the record.
        f2.contractual_issue_date = "2025-01-01"
        f2.description = "This should pass"
        f2.save()

        self.assertEqual(self.task.contractual_issue_date, Date.to_date("2025-01-01"))
