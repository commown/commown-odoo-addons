from lxml import html

from odoo import http
from odoo.tests import HttpCase

from odoo.addons.product_rental.tests.common import RentalSaleOrderTC


def html_page(response):
    return html.fromstring(response.text)


class WebsiteSaleB2BAddressTC(RentalSaleOrderTC, HttpCase):
    def test_company_infos_on_shop_address(self):
        "Company infos are editable on /shop/address when no partner company is set"
        # Setup (B2B website setting + add product to cart)
        partner = self.env.ref("base.partner_demo_portal")
        self.authenticate(partner.user_ids.login, "portal")
        partner.website_id = self.ref("website_b2b.b2b_website")

        csrf_token = http.Request.csrf_token(self)

        product = self.env.ref("product.product_delivery_02_product_template")
        self.opener.post(
            self.base_url() + "/shop/cart/update",
            data={
                "product_id": product.product_variant_id.id,
                "csrf_token": csrf_token,
            },
        )

        # Case 1: the partner has no company
        data = {"csrf_token": csrf_token, "partner_id": partner.id}

        address_page = html_page(self.url_open("/shop/address", data=data))

        inputs = [i.get("name") for i in address_page.xpath("//input[not(@disabled)]")]
        self.assertIn("company_name", inputs)
        self.assertIn("vat", inputs)

        # Case 2: the partner has a company
        partner.create_company()

        address_page = html_page(self.url_open("/shop/address", data=data))
        inputs = {i.get("name"): i for i in address_page.xpath("//input")}

        self.assertIn("company_name", inputs)
        self.assertIn("disabled", inputs["company_name"].keys())

        self.assertIn("vat", inputs)
        self.assertIn("disabled", inputs["vat"].keys())
