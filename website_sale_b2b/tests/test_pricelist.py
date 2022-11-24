from .common import RentedQuantityTC


def _add_attr(product, attr_name, value_prices):
    attr = product.env["product.attribute"].create({"name": attr_name})

    attr_values = product.env["product.attribute.value"]
    for value in value_prices:
        attr_values |= attr_values.create({"attribute_id": attr.id, "name": value})

    attr_lines = {"attribute_id": attr.id, "value_ids": [(6, 0, attr_values.ids)]}
    product.update({"attribute_line_ids": [(0, 0, attr_lines)]})

    for attr_value in attr_values:
        product.env["product.template.attribute.value"].create(
            {
                "product_tmpl_id": product.id,
                "price_extra": value_prices[attr_value.name],
                "attribute_id": attr.id,
                "product_attribute_value_id": attr_value.id,
            }
        )


class PricelistTC(RentedQuantityTC):
    def setUp(self):
        super().setUp()
        self.pricelist = self.env["product.pricelist"].create(
            {"name": "test", "account_for_rented_quantity": "product-category"}
        )
        self.pricelist.account_for_rented_quantity_category_ids |= self.cat_fp

        self.env["product.pricelist.item"].create(
            {
                "pricelist_id": self.pricelist.id,
                "applied_on": "1_product",
                "product_tmpl_id": self.fp_premium.id,
                "compute_price": "percentage",
                "percent_price": 20.0,
                "min_quantity": 10,
            }
        )

    def unit_price(self, quantity, product, partner=None, pricelist=None):
        partner = partner or self.so.partner_id
        pricelist = pricelist or self.pricelist
        return pricelist.get_products_price(product, (quantity,), partner)[product.id]

    def test_account_for_rented_quantity(self):

        partner = self.so.partner_id
        # Check test prerequisite:
        self.assertEqual(partner.rented_quantity(product_template=self.fp_premium), 1)
        self.assertEqual(partner.rented_quantity(product_template=self.fp2), 1)

        self.assertEqual(
            {self.fp_premium.id: 60.0},
            self.pricelist.get_products_price(self.fp_premium, (7,), partner),
        )

        self.assertEqual(
            {self.fp_premium.id: 48.0},
            self.pricelist.get_products_price(self.fp_premium, (8,), partner),
        )

    def test_no_extra_reduction(self):
        "compute_price field makes it possible to exclude extra prices from reductions"

        _add_attr(self.fp_premium, "Power", {"Low": 0.0, "Medium": 5.0, "High": 10.0})
        _add_attr(self.fp_premium, "Service", {"Basic": 0.0, "Premium": 3.0})

        variants = {
            tuple(p.attribute_value_ids.mapped("name")): p
            for p in self.fp_premium.product_variant_ids
        }

        self.assertEqual(self.unit_price(10, variants[("Low", "Basic")]), 48.0)
        self.assertEqual(self.unit_price(10, variants[("Medium", "Premium")]), 54.4)

        self.pricelist.item_ids.update({"percentage_exclude_extra": True})

        self.assertEqual(self.unit_price(10, variants[("Low", "Basic")]), 48.0)
        self.assertEqual(self.unit_price(10, variants[("Medium", "Premium")]), 56.0)
