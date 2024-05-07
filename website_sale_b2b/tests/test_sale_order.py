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

    def _add_partner_to_b2b_portal(self, partner):
        b2b_website = self.env.ref("website_sale_b2b.b2b_website")
        wiz = self.env["portal.wizard"].with_context(active_ids=[partner.id]).create({})
        wiz.user_ids.update({"in_portal": True, "website_id": b2b_website.id})
        wiz.action_apply()

    def test_is_big_b2b(self):
        def set_big_b2b_qty(value):
            self.env["ir.config_parameter"].set_param(
                "website_sale_b2b.big_b2b_min_qty",
                value,
            )

        self._add_partner_to_b2b_portal(self.so.partner_id)
        set_big_b2b_qty(0)  # Make sure we are above the threshold

        # Test when all conditions are fulfilled:
        self.assertTrue(self.so.is_big_b2b())

        # Remove the "big" B2B condition and check the result is False:
        set_big_b2b_qty(1000)  # Make sure we are below the threshold
        self.assertFalse(self.so.is_big_b2b())

        # Re-add the "big" B2B condition but remove the B2B website one:
        set_big_b2b_qty(0)
        self.so.partner_id.user_ids.update({"website_id": False})
        self.assertFalse(self.so.is_big_b2b())
