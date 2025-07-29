from pathlib import Path

from lxml import html
from werkzeug.test import Client
from werkzeug.wrappers import Response

from odoo import http
from odoo.tests import HttpCase, get_db_name

from odoo.addons.product_rental.tests.common import RentalSaleOrderMixin

HERE = (Path(__file__) / "..").resolve()


class CustomerPortalMixin(RentalSaleOrderMixin):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env.ref("base.partner_demo_portal")
        cls.partner.signup_prepare()
        cls.werkzeug_environ = {"REMOTE_ADDR": "127.0.0.1"}
        cls.headers = {}

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
        self.assertEqual(len(page.forms), 1)
        return dict(page.forms[0].form_values())

    def portal_client(self):
        user = self.partner.user_ids.ensure_one()
        test_client = Client(http.root, Response)

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
        self.assertEqual(response.status_code, 303)
        self.assertIn("/my/account", response.location)
        return test_client


class AdministrativeDocsCustomerPortalTC(CustomerPortalMixin, HttpCase):
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

        self.assertEqual(response.status_code, 303)
        self.assertIn("/my/home", response.data.decode("utf-8"))

        with self.registry.cursor() as test_cursor:
            env = self.env(test_cursor)
            partner = env["res.partner"].browse(self.partner.id)
            self.assertTrue(partner.id_card1)
