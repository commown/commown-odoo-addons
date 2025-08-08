from lxml import html

from odoo.addons.website_sale_partner_firstname.tests import common


class CommownShippingSaleAddressControllerTC(common.WebsiteSaleControllerTC):
    timeout = 99999

    def assertShippingMode(self, html_text):
        """
        When returning the request after a failure, the address mode (shipping/billing)
        is passed to the website_sale.address and used in the country_id select field.
        """
        mode = html.fromstring(html_text).xpath(
            "//form//select[@name='country_id']/@mode"
        )
        self.assertEqual(mode, ["shipping"])

    def test_commown_shipping_validation(self):
        """
        When submitting the /shop/address request for a shipping address :
        - The address lines must be lower than MAX_ADDRESS_SIZE;
        - The email must be provided;
        """
        # Setup
        partner = self.env.ref("base.partner_demo_portal")
        max_address_size = partner.MAX_ADDRESS_SIZE

        self.assertEqual(partner.user_ids.login, "portal")

        self.authenticate("portal", "portal")
        self.add_product_to_user_cart()

        def _address(**kwargs):
            kwargs["csrf_token"] = self.csrf_token(self.url_open("/shop/address").text)
            return self.post("/shop/address", data=kwargs)

        # Fetch base data inserted in /shop/address
        page = html.fromstring(_address(partner_id=partner.id))
        form_values = page.forms[0].form_values()

        base_data = {k: v for k, v in form_values if k in partner._fields}
        base_data["submitted"] = True

        # We can insure that the following /shop/address requests are considered for shipping,
        # as the address controller endpoint default to a ('new', 'shipping') mode if partner_id is empty.

        # Fail state 1: the address line is too big
        text = _address(**dict(base_data, street="A" * (max_address_size + 1)))
        self.assertShippingMode(text)
        self.assertIn("length is limited to %s" % max_address_size, text)
        self.assertEqual(
            ["street"],
            html.fromstring(text).xpath("//form//input[hasclass('is-invalid')]/@name"),
        )

        # Fail state 2: There's no email address
        text = _address(**dict(base_data, email=""))
        self.assertShippingMode(text)
        self.assertIn("Some required fields are empty.", text)
        self.assertEqual(
            ["email"],
            html.fromstring(text).xpath("//form//input[hasclass('is-invalid')]/@name"),
        )
