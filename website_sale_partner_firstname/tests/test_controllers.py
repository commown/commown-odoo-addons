from lxml import html

from odoo import http

from .common import WebsiteSaleControllerTC


class WebsiteSaleFirstnameControllerTC(WebsiteSaleControllerTC):
    def test_checkout_form_validate(self):
        # Setup
        partner = self.env.ref("base.partner_demo_portal")
        self.assertEqual(partner.user_ids.login, "portal")

        self.authenticate("portal", "portal")
        self.add_product_to_user_cart()
        so_id = http.root.session_store.get(self.session.sid)["sale_order_id"]

        def _address(**kwargs):
            kwargs["csrf_token"] = self.csrf_token(self.url_open("/shop/address").text)
            return self.post("/shop/address", data=kwargs)

        page = html.fromstring(_address(partner_id=partner.id))

        # Check the name input replacement
        self.assertFalse(page.xpath("//input[@name='name']"))

        self.assertTrue(page.xpath("//input[@name='firstname']"))
        self.assertTrue(page.xpath("//input[@name='lastname']"))

        # Fetch base data inserted in /shop/address
        form_values = page.forms[0].form_values()

        base_data = {k: v for k, v in form_values if k in partner._fields}
        base_data["submitted"] = True

        # Situation 1: the firstname field is not filled.
        text = _address(**dict(base_data, firstname=""))

        self.assertIn("Some required fields are empty.", text)
        self.assertEqual(
            html.fromstring(text).xpath("//form//input[hasclass('is-invalid')]/@name"),
            ["firstname"],
        )

        # Situation 2: the firstname and lastname fields are filled.
        valid_data = dict(base_data, firstname="Firstname", lastname="Lastname")
        text = _address(**valid_data)

        so = self.env["sale.order"].browse(so_id)
        self.assertTrue(so.partner_shipping_id != so.partner_id)

        self.assertEqual(so.partner_shipping_id.firstname, "Firstname")
        self.assertEqual(so.partner_shipping_id.lastname, "Lastname")
