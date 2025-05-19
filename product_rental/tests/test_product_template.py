from odoo.tests.common import TransactionCase


class ProductTemplateTC(TransactionCase):
    "Test for the product template methods of present module"

    def test_onchange_is_contract(self):
        prod = self.env.ref("product_rental.prod_pc")

        # Check test prerequisite
        self.assertTrue(prod.is_contract)

        # Check onchange_is_contract:
        prod.has_recurrent_payment = False
        prod.onchange_is_contract()
        self.assertTrue(prod.has_recurrent_payment)

        prod.is_contract = False
        prod.has_recurrent_payment = False
        prod.onchange_is_contract()
        self.assertFalse(prod.has_recurrent_payment)

        prod.is_contract = False
        prod.has_recurrent_payment = True
        prod.onchange_is_contract()
        self.assertTrue(prod.has_recurrent_payment)
