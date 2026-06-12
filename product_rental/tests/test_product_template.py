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

    def test_recurrent_payment_amount_ratio(self):
        prod = self.env.ref("product_rental.prod_pc")
        self.assertEqual(prod.recurrent_payment_amount_ratio(), 2.0)

        prod.list_price = 0.0
        self.assertEqual(prod.recurrent_payment_amount_ratio(), 1.0)

        prod.has_recurrent_payment = False
        self.assertIsNone(prod.recurrent_payment_amount_ratio())
