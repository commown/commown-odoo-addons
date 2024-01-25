from pathlib import Path

from lxml import html
from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse

from odoo.service import wsgi_server
from odoo.tests.common import HttpCase, get_db_name

from odoo.addons.product_rental.tests.common import (
    MockedEmptySessionMixin,
    RentalSaleOrderMixin,
)

HERE = (Path(__file__) / "..").resolve()


class CustomerPortalMixin(RentalSaleOrderMixin, MockedEmptySessionMixin):
    def setUp(self):
        super().setUp()
        self.partner = self.env.ref("base.partner_demo_portal")
        self.partner.signup_prepare()
        self.env.cr.commit()
        self.werkzeug_environ = {"REMOTE_ADDR": "127.0.0.1"}
        self.headers = {}

    def get_page(self, test_client, path, **data):
        "Return an lxml doc obtained from the html at given url path"
        response = test_client.get(
            path,
            query_string=data,
            follow_redirects=True,
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 200, " - ".join((path, response.status)))
        return html.fromstring(response.data)

    def get_form(self, test_client, path, **data):
        "Get given page and return a name: value dict of its inputs and selects"
        page = self.get_page(test_client, path, **data)
        form = {n.get("name"): n.get("value") for n in page.xpath("//input")}
        for select in page.xpath("//select"):
            form[select.get("name")] = select.xpath("string(option[@selected]/@value)")
        return form

    def portal_client(self):
        user = self.partner.user_ids.ensure_one()
        test_client = Client(wsgi_server.application, BaseResponse)

        login_form = self.get_form(test_client, "/web/login/", db=get_db_name())
        login_form.update(
            {
                "login": user.login,
                "password": "portal",
                "redirect": "/my/account",
            }
        )
        response = test_client.post(
            "/web/login/",
            data=login_form,
            environ_base=self.werkzeug_environ,
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("/my/account", str(response.data))
        return test_client


class CustomerPortalB2CTC(CustomerPortalMixin, HttpCase):
    def test_documents(self):
        """Portal users must be able to post their documents
        ... and see the upload state on their home page
        """

        test_client = self.portal_client()

        # Post id_card1
        account_form = self.get_form(test_client, "/my/account")

        with open(HERE / "smallest.pdf", "rb") as fobj:
            account_form.update(
                {
                    "redirect": "/my/home",
                    "id_card1": (fobj, "card1.pdf"),
                    "id_card2": "",
                    "proof_of_address": "",
                }
            )
            response = test_client.post(
                "/my/account", data=account_form, environ_base=self.werkzeug_environ
            )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/my/home", response.data.decode("utf-8"))

        with self.registry.cursor() as test_cursor:
            env = self.env(test_cursor)
            partner = env["res.partner"].browse(self.partner.id)
            self.assertTrue(partner.id_card1)

    def test_invoices(self):

        test_client = self.portal_client()

        # Test without any invoice and check resulting page
        doc = self.get_page(test_client, "/my/invoices")
        self.assertTrue(
            doc.xpath(
                "//p[text()='There are currently no"
                " invoices and payments for your account.']"
            )
        )

        # Add some invoices and check resulting invoice links
        with self.registry.cursor() as test_cursor:
            env = self.env(test_cursor)
            partner = env["res.partner"].browse(self.partner.id)
            invs = self.generate_contract_invoices(partner)
            self.assertTrue(len(invs) > 2)
            invs[0].action_invoice_open()
            invs[2].action_invoice_open()
        doc = self.get_page(test_client, "/my/invoices")
        hrefs = doc.xpath("//*[hasclass('o_portal_my_doc_table')]//a/@href")
        self.assertTrue(
            {href.split("?", 1)[0] for href in hrefs},
            {"/my/invoices/%d" % inv.id for inv in (invs[0], invs[2])},
        )
        self.assertTrue(all("report_type=pdf" in href for href in hrefs))

        resp = test_client.get(hrefs[0])
        self.assertEqual(resp.headers["Content-Type"], "application/pdf")

    def _create_attachment(self, env, name, lang):
        return env["ir.attachment"].create(
            {
                "name": name,
                "type": "binary",
                "datas": "toto",
                "lang": lang,
                "public": True,
            }
        )

    def test_order_page(self):

        test_client = self.portal_client()

        with self.registry.cursor() as test_cursor:
            env = self.env(test_cursor)
            partner = env["res.partner"].browse(self.partner.id)
            so = self.create_sale_order(partner, env=env)
            # Add contractual documents to test the corresponding section
            ct = so.mapped("order_line.product_id.property_contract_template_id")[0]
            doc1 = self._create_attachment(env, "doc 1", False)
            doc2 = self._create_attachment(env, "doc 2", False)
            ct.contractual_documents |= doc1 | doc2
            # > Remove report from default template to add ours:
            env.ref("sale.email_template_edi_sale").report_template = False
            # Add a coupon to test the corresponding section
            campaign = env["coupon.campaign"].create(
                {
                    "name": "Test campaign",
                    "seller_id": env.ref("base.res_partner_2").id,
                }
            )
            env["coupon.coupon"].create(
                {
                    "campaign_id": campaign.id,
                    "code": "TEST",
                    "used_for_sale_id": so.id,
                }
            )
            so.action_confirm()

        doc = self.get_page(test_client, "/my/orders/%d" % so.id)

        # Check sidebar is gone, and in particular the pdf download link
        self.assertFalse(doc.xpath("//*[@id='sidebar_content']"))
        self.assertFalse(
            doc.xpath(
                "//a[starts-with(@href, '/my/orders/%d')"
                " and contains(@href, 'pdf')]/@href" % so.id
            )
        )
        self.assertTrue(doc.xpath("//section[@id='coupons']"))
        self.assertEqual(
            sorted(doc.xpath("//section[@id='sent_docs']//li//a//span/text()")),
            ["doc 1", "doc 2"],
        )
        self.assertFalse(doc.xpath("//div[@id='sale_order_communication']"))

    def test_task_page(self):

        test_client = self.portal_client()

        with self.registry.cursor() as test_cursor:
            env = self.env(test_cursor)
            task = env.ref("project.project_task_1")
            # Test pre-condition
            self.assertIn(self.partner, task.mapped("message_follower_ids.partner_id"))

        doc = self.get_page(test_client, "/my/task/%d" % task.id)
        self.assertEqual(
            doc.xpath("//*[text()='Assigned to']/..//span[@itemprop]/@itemprop"),
            ["name"],
        )

    def test_no_company_infos_on_account(self):
        account_page = self.get_page(self.portal_client(), "/my/account")

        labels = account_page.xpath("//label/@for")
        self.assertNotIn("company_name", labels)
        self.assertNotIn("vat", labels)


class CustomerPortalB2BTC(CustomerPortalMixin, HttpCase):
    def setUp(self):
        super().setUp()
        self.headers["Host"] = "b2b.local"

        with self.registry.cursor() as test_cursor:
            partner = self._partner(test_cursor)
            partner.website_id = partner.env.ref("website_sale_b2b.b2b_website").id
            partner.website_id.update(
                {"domain": self.headers["Host"], "login_checkbox_message": "I'm a pro"}
            )

    def _partner(self, test_cursor):
        env = self.env(test_cursor)
        return env["res.partner"].browse(self.partner.id)

    def test_company_infos_on_account(self):
        account_page = self.get_page(self.portal_client(), "/my/account")

        labels = account_page.xpath("//label/@for")
        self.assertIn("company_name", labels)
        self.assertIn("vat", labels)

        inputs = [i.get("name") for i in account_page.xpath("//input[not(@disabled)]")]
        self.assertNotIn("company_name", inputs)
        self.assertNotIn("vat", inputs)

    def test_company_infos_on_shop_address(self):
        "company infos are editable on /shop/address no partner company is set"
        with self.registry.cursor() as test_cursor:
            partner = self._partner(test_cursor)
            so = self.create_sale_order(partner, env=partner.env)
            so.website_id = partner.website_id.id

        test_client = self.portal_client()
        account_page = self.get_page(test_client, "/my/account")

        labels = account_page.xpath("//label/@for")
        self.assertIn("company_name", labels)
        self.assertIn("vat", labels)

        address_page = self.get_page(
            test_client, "/shop/address", partner_id=partner.id
        )
        inputs = [i.get("name") for i in address_page.xpath("//input[not(@disabled)]")]
        self.assertIn("company_name", inputs)
        self.assertIn("vat", inputs)

        with self.registry.cursor() as test_cursor:
            self._partner(test_cursor).create_company()

        address_page = self.get_page(
            test_client, "/shop/address", partner_id=partner.id
        )
        inputs = {i.get("name"): i for i in address_page.xpath("//input")}

        self.assertIn("company_name", inputs)
        self.assertIn("disabled", inputs["company_name"].keys())

        self.assertIn("vat", inputs)
        self.assertIn("disabled", inputs["vat"].keys())
