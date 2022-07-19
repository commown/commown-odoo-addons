from odoo.exceptions import ValidationError

from odoo.addons.contract.tests.test_contract import TestContractBase


class ContractTC(TestContractBase):
    def test_inverse_recurring_next_date_error(self):
        self.contract.is_auto_pay = False
        init_recurring_next_date = self.contract.recurring_next_date
        self.contract.recurring_create_invoice()

        with self.assertRaises(ValidationError) as err:
            self.contract.recurring_next_date = init_recurring_next_date

        self.assertIn(
            "There are invoices past the new next recurring date", str(err.exception)
        )

    def test_inverse_recurring_next_date_ok(self):
        self.contract.is_auto_pay = False
        init_recurring_next_date = self.contract.recurring_next_date
        inv = self.contract.recurring_create_invoice()

        inv.unlink()
        self.contract.recurring_next_date = init_recurring_next_date

        self.assertEqual(
            set(self.contract.mapped("contract_line_ids.recurring_next_date")),
            {init_recurring_next_date},
        )
