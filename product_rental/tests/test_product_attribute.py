from odoo.tests.common import TransactionCase


class ProductAttributeTemplateValueTC(TransactionCase):
    def setUp(self):
        super().setUp()
        self.product = self.env.ref("product_rental.prod_pc")
        self.ptav = self.env["product.template.attribute.value"].search(
            [("product_tmpl_id", "=", self.product.id)], limit=1
        )

    def test_compute_recurrent_payment_amount_extra(self):
        self.assertTrue(self.ptav.has_recurrent_payment)
        self.ptav.price_extra = 10.0
        self.assertEqual(self.ptav.recurrent_payment_amount_extra, 5.0)

    def test_inverse_recurrent_payment_amount_extra(self):
        self.assertTrue(self.ptav.has_recurrent_payment)
        self.ptav.recurrent_payment_amount_extra = 13.0
        self.assertEqual(self.ptav.price_extra, 26.0)
