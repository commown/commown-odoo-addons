from odoo.addons.contract.tests.test_contract import TestContractBase


class ContractPaymentTC(TestContractBase):
    def test_amount(self):
        "Contract amount does not take"

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
