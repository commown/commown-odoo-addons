from .common import RentedQuantityTC


class PricelistTC(RentedQuantityTC):
    def test_account_for_rented_quantity(self):
        pricelist = self.env["product.pricelist"].create(
            {"name": "test", "account_for_rented_quantity": "product-category"}
        )
        pricelist.account_for_rented_quantity_category_ids |= self.cat_fp

        self.env["product.pricelist.item"].create(
            {
                "pricelist_id": pricelist.id,
                "applied_on": "1_product",
                "product_tmpl_id": self.fp_premium.id,
                "compute_price": "percentage",
                "percent_price": 20.0,
                "min_quantity": 10,
            }
        )

        partner = self.so.partner_id
        # Check test prerequisite:
        self.assertEqual(partner.rented_quantity(product_template=self.fp_premium), 1)
        self.assertEqual(partner.rented_quantity(product_template=self.fp2), 1)

        self.assertEqual(
            {self.fp_premium.id: 60.0},
            pricelist.get_products_price(self.fp_premium, (7,), partner),
        )

        self.assertEqual(
            {self.fp_premium.id: 48.0},
            pricelist.get_products_price(self.fp_premium, (8,), partner),
        )
