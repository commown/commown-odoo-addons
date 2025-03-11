from odoo.tests.common import TransactionCase


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
        project = self.env.ref("project.project_project_1")
        self.task = self.env["project.task"].create(
            {"name": "Test task", "project_id": project.id, "partner_id": False}
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
