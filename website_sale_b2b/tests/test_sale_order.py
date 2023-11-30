from odoo.addons.product_rental.tests.common import RentalSaleOrderTC


class SaleOrderLineTC(RentalSaleOrderTC):
    def setUp(self):
        super().setUp()
        self.so = self.create_sale_order()

    def test_description_sale(self):
        so_line = self.so.order_line.filtered("product_id.is_rental")[0]

        pt = so_line.product_id.product_tmpl_id
        pt.update(
            {
                "description_sale_is_template": True,
                "website_id": self.env.ref("website_sale_b2b.b2b_website").id,
            }
        )
        prefix = so_line.product_id.display_name + "\n"

        pt.description_sale = "${record.display_rental_price()}"
        so_line.price_unit = 20

        company_currency = self.env["res.company"].browse(1).currency_id.name
        expected = {
            "EUR": "10.00 € excl. taxes Monthly",
            "USD": "$ excl. taxes\xa010.00 Monthly",
        }
        self.assertEqual(so_line.name, prefix + expected[company_currency])

        pt.description_sale = "${record.display_commitment_duration()}"
        so_line._onchange_recompute_name()
        self.assertEqual(so_line.name, prefix + "12 month(s)")

    def test_action_quotation_send(self):
        self.so.partner_id.website_id = self.env.ref("website_sale_b2b.b2b_website").id
        action = self.so.action_quotation_send()
        self.assertEqual(
            action["context"]["default_template_id"],
            self.env.ref("website_sale_b2b.email_template_edi_sale").id,
        )
