from lxml import html

from odoo import http
from odoo.tests import HttpCase, tagged


def html_page(response):
    return html.fromstring(response.text)


@tagged("-at_install", "post_install")
class CustomerPortalB2CTC(HttpCase):
    def test_no_company_infos_on_account(self):
        # Setup
        partner = self.env.ref("base.partner_demo_portal")

        self.authenticate(partner.user_ids.login, "portal")
        partner.website_id = self.ref("website.default_website")

        # Accessing the page
        data = {"csrf_token": http.Request.csrf_token(self)}
        account_page = html_page(self.url_open("/my/account", data=data))

        labels = account_page.xpath("//label/@for")
        self.assertNotIn("company_name", labels)
        self.assertNotIn("vat", labels)


@tagged("-at_install", "post_install")
class CustomerPortalB2BTC(HttpCase):
    def test_company_infos_on_account(self):
        # Setup
        partner = self.env.ref("base.partner_demo_portal")

        self.authenticate(partner.user_ids.login, "portal")
        partner.website_id = self.ref("website_b2b.b2b_website")

        # Accessing the page
        data = {"csrf_token": http.Request.csrf_token(self)}
        account_page = html_page(self.url_open("/my/account", data=data))

        labels = account_page.xpath("//label/@for")
        self.assertIn("company_name", labels)
        self.assertIn("vat", labels)

        inputs = [i.get("name") for i in account_page.xpath("//input[not(@disabled)]")]
        self.assertNotIn("company_name", inputs)
        self.assertNotIn("vat", inputs)
