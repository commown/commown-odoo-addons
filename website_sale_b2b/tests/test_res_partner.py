from .common import RentedQuantityTC


class ResPartnerTC(RentedQuantityTC):
    def test_rented_quantity(self):
        rented_quantity = self.so.partner_id.rented_quantity
        self.assertEqual(rented_quantity(product_template=self.fp_premium), 1)
        self.assertEqual(rented_quantity(product_template=self.fp2), 1)
        self.assertEqual(rented_quantity(product_category=self.cat_fp), 2)
        self.assertEqual(rented_quantity(product_category=self.cat_fp_premium), 1)
