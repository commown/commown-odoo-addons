from datetime import date

from lxml import html

from odoo.tests import HttpCase

from .common import SponsoringTC


class SponsoringCustomerPortalTC(SponsoringTC, HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.contract = cls.create_contract(cls.partner)

    def _get_customer_portal(self):
        self.authenticate("portal", "portal")

        res = self.url_open("/my", allow_redirects=False)
        self.assertEqual(res.status_code, 200)

        return html.fromstring(res.text)

    def test_portal_no_active_contract(self):
        "No sponsoring section should appear on the portal of a customer without any contracts"
        page = self._get_customer_portal()
        self.assertFalse(page.xpath("//div[hasclass('o_portal_sponsoring')]"))

    def test_portal_active_contract(self):
        self.contract.date_start = date.today()

        page = self._get_customer_portal()
        self.assertTrue(page.xpath("//div[hasclass('o_portal_sponsoring')]"))

        sponsor_text = "".join(
            page.xpath("//div[hasclass('o_portal_sponsoring')]/descendant::text()")
        )

        self.assertIn(self.partner.sponsor_code, sponsor_text)
