from odoo.addons.product_rental.tests.common import RentalSaleOrderTC


class SaleOrderLineTC(RentalSaleOrderTC):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.so = cls.create_sale_order()

    def test_description_sale(self):
        so_line = self.so.order_line.filtered("product_id.has_recurrent_payment")[0]

        pt = so_line.product_id.product_tmpl_id
        pt.update(
            {
                "description_sale_is_template": True,
                "website_id": self.env.ref("website_b2b.b2b_website").id,
            }
        )
        prefix = so_line.product_id.display_name + "\n"

        # Testing value printing
        pt.description_sale = "${record.display_recurrent_payment_amount()}"
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

        # Testing variable declaration
        pt.description_sale = "<% set dummy_value = 'Dummy value'%> - ${dummy_value}"
        so_line._onchange_recompute_name()
        self.assertEqual(so_line.name, prefix + " - Dummy value")

    def test_sale_confirmation_with_b2b_email(self):
        "When an order is confirmed through a transaction, the B2B confirmation mail should be used"
        # Setup - payment records
        provider = self.env.ref("payment.payment_provider_demo")
        provider.state = "test"

        inbound_pay_meth = provider.journal_id.inbound_payment_method_line_ids
        inbound_pay_meth.payment_provider_id = provider

        def _create_and_confirm_tx_for_so(so):
            tx = self.env["payment.transaction"].create(
                {
                    "amount": so.amount_total,
                    "partner_id": so.partner_id.id,
                    "provider_id": provider.id,
                    "currency_id": self.env.company.currency_id.id,
                }
            )
            so.transaction_ids = tx

            tx._set_done()
            tx._reconcile_after_done()

            return tx

        # Since the message objects don't possess a value linking to the used template,
        # we insert a test-specific value to insure this is the used template.
        b2b_template = self.env.ref("website_sale_b2b.mail_template_sale_confirmation")
        debug_text = f"<!-- tmp - {self.so.create_date} -->"
        b2b_template.body_html += debug_text

        # Case 1: the confirmation email is sent to a B2C partner
        self.so.partner_id.website_id = self.env.ref("website.default_website")

        _create_and_confirm_tx_for_so(self.so)

        b2c_confirm_msg = self.so.message_ids.filtered(
            lambda m: m.subtype_id == self.env.ref("mail.mt_comment")
        )
        self.assertTrue(b2c_confirm_msg)
        self.assertNotIn(debug_text, b2c_confirm_msg.body)

        # Case 2: the confirmation email is sent to a B2B partner
        b2b_partner = self.env.ref("base.partner_demo_portal")
        b2b_partner.website_id = self.env.ref("website_b2b.b2b_website")
        so_b2b = self.create_sale_order(partner=b2b_partner)

        _create_and_confirm_tx_for_so(so_b2b)

        b2b_confirm_msg = so_b2b.message_ids.filtered(
            lambda m: m.subtype_id == self.env.ref("mail.mt_comment")
        )
        self.assertTrue(b2b_confirm_msg)
        self.assertIn(debug_text, b2b_confirm_msg.body)

    def _add_partner_to_b2b_portal(self, partner):
        b2b_website = self.env.ref("website_b2b.b2b_website")
        wiz = self.env["portal.wizard"].with_context(active_ids=[partner.id]).create({})
        wiz.user_ids.update({"website_id": b2b_website.id})
        wiz.user_ids.filtered(
            lambda u, p=partner: u.partner_id == p
        ).action_grant_access()

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
