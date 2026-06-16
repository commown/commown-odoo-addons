from base64 import b64encode
from pathlib import Path

from lxml import html

from odoo.http import root
from odoo.tests import HttpCase

from odoo.addons.product_rental.tests.common import RentalSaleOrderMixin

HERE = (Path(__file__) / "..").resolve()


def _get_dummy_document():
    with open(HERE / "smallest.pdf", "rb") as fobj:
        doc = b64encode(fobj.read())
    return doc


class CommonSaleAdminDocsMixin(RentalSaleOrderMixin):
    # Fields to overwrite
    req_url = None
    session_field = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.b2b_website = cls.env.ref("website_b2b.b2b_website")
        cls.partner = cls.env.ref("base.partner_demo_portal")
        cls.so = cls.create_sale_order(cls.partner)

    def _get_docs_reminder_el(self, page):
        return page.xpath("//div[@id='admin_docs_reminder']")

    def _get_docs_desc(self, page):
        return "".join(
            page.xpath("//div[@id='admin_docs_reminder']/descendant-or-self::text()")
        )

    def _set_so_and_get_shop_page(self, is_b2b=False):
        session = self.authenticate("portal", "portal")

        if is_b2b:
            # Setting the B2B site before logging in leads to a login error.
            self.partner.website_id = self.b2b_website

        # We set the sale order, so that we don't get redirected by the controllers.
        session[self.session_field] = self.so.id
        root.session_store.save(session)

        res = self.url_open(self.req_url, allow_redirects=False)
        self.assertEqual(res.status_code, 200)

        page_html = html.fromstring(res.text)
        return page_html

    def test_docs_reminder_b2c(self):
        page = self._set_so_and_get_shop_page()

        self.assertTrue(self._get_docs_reminder_el(page))
        self.assertIn("justificatif de domicile", self._get_docs_desc(page))

    def test_docs_reminder_b2b(self):
        page = self._set_so_and_get_shop_page(is_b2b=True)

        self.assertTrue(self._get_docs_reminder_el(page))
        self.assertIn("kbis", self._get_docs_desc(page).lower())

    def test_docs_already_set_b2c(self):
        doc = _get_dummy_document()
        self.partner.write({"id_card1": doc, "proof_of_address": doc})

        page = self._set_so_and_get_shop_page()
        self.assertFalse(self._get_docs_reminder_el(page))

    def test_docs_already_set_b2b(self):
        doc = _get_dummy_document()
        self.partner.write({"id_card1": doc, "company_record": doc})

        page = self._set_so_and_get_shop_page(is_b2b=True)
        self.assertFalse(self._get_docs_reminder_el(page))


class PaymentSaleAdminDocsTC(CommonSaleAdminDocsMixin, HttpCase):
    req_url = "/shop/payment"
    session_field = "sale_order_id"


class ConfirmationSaleAdminDocsTC(CommonSaleAdminDocsMixin, HttpCase):
    req_url = "/shop/confirmation"
    session_field = "sale_last_order_id"
