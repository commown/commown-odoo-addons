from odoo.addons.product_rental.tests.test_website import WebsiteBaseTC


class PaymentPortalTemplatesTC(WebsiteBaseTC):
    def setUp(self):
        super().setUp()

    def test_render_payment_portal_templates(self):
        view = self.render_view(
            "website_sale_b2b.payment_tokens_list",
            is_big_b2b=True,
            is_authorized_to_order=True,
        )
        self.assertIn("Submit my request", view.text_content())
