from lxml import html

from odoo.http import root
from odoo.tests import HttpCase

from odoo.addons.product_rental.tests.common import RentalSaleOrderTC


class WebsiteSaleAdminDocsTC(RentalSaleOrderTC, HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.b2b_website = cls.env.ref("website_b2b.b2b_website")
        cls.partner = cls.env.ref("base.partner_demo_portal")
        cls.so = cls.create_sale_order(cls.partner)

    def _login_and_set_sale_order(self, so, page):
        session = self.authenticate("portal", "portal")
        match page:
            case "payment":
                session["sale_order_id"] = so.id
            case "confirmation":
                session["sale_last_order_id"] = so.id
            case _:  # pragma: no cover
                raise ValueError("Incorrect page type")

        root.session_store.save(session)

    def test_docs_reminder_in_payment_b2c(self):
        self._login_and_set_sale_order(self.so, "payment")

        req = self.url_open("/shop/payment", allow_redirects=False)
        self.assertEqual(req.status_code, 200)

        page = html.fromstring(req.text)

        self.assertTrue(page.xpath("//div[@id='admin_docs_reminder']"))
        docs_desc = "".join(page.xpath("//div[@id='admin_docs_reminder']//a/text()"))
        self.assertIn("justificatif de domicile", docs_desc)

    def test_docs_reminder_in_payment_b2b(self):
        self._login_and_set_sale_order(self.so, "payment")
        self.partner.website_id = self.b2b_website

        req = self.url_open("/shop/payment", allow_redirects=False)
        self.assertEqual(req.status_code, 200)

        page = html.fromstring(req.text)

        self.assertTrue(page.xpath("//div[@id='admin_docs_reminder']"))
        docs_desc = "".join(page.xpath("//div[@id='admin_docs_reminder']//a/text()"))
        self.assertIn("KBIS", docs_desc)

    def test_docs_reminder_in_confirmation_b2c(self):
        self._login_and_set_sale_order(self.so, "confirmation")

        req = self.url_open("/shop/confirmation", allow_redirects=False)
        self.assertEqual(req.status_code, 200)

        page = html.fromstring(req.text)

        self.assertTrue(page.xpath("//div[@id='admin_docs_reminder']"))
        docs_desc = "".join(page.xpath("//div[@id='admin_docs_reminder']/text()"))
        self.assertIn("justificatif de domicile", docs_desc)

    def test_docs_reminder_in_confirmation_b2b(self):
        self._login_and_set_sale_order(self.so, "confirmation")
        self.partner.website_id = self.b2b_website

        req = self.url_open("/shop/confirmation", allow_redirects=False)
        self.assertEqual(req.status_code, 200)

        page = html.fromstring(req.text)

        self.assertTrue(page.xpath("//div[@id='admin_docs_reminder']"))
        docs_desc = "".join(page.xpath("//div[@id='admin_docs_reminder']/text()"))
        self.assertIn("Kbis", docs_desc)
