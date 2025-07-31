from lxml import html
from werkzeug.test import Client
from werkzeug.wrappers import Response

from odoo import http
from odoo.tests.common import HttpCase, get_db_name


class ResPartnerResetPasswordTC(HttpCase):
    def setUp(self):
        super().setUp()
        self.test_client = Client(http.root, Response)
        self.werkzeug_environ = {"REMOTE_ADDR": "127.0.0.1"}

        self.partner = self.env.ref("base.partner_demo_portal")
        self.partner.signup_prepare()

    def get_page(self, test_client, path, **data):
        "Return an lxml doc obtained from the html at given url path"
        response = test_client.get(path, query_string=data, follow_redirects=True)
        self.assertEqual(response.status_code, 200, path)
        return html.fromstring(response.data)

    def get_form(self, test_client, path, **data):
        "Get given page and return a name: value dict of its inputs and selects"
        page = self.get_page(test_client, path, **data)
        form = {n.get("name"): n.get("value") for n in page.xpath("//input")}
        for select in page.xpath("//select"):
            form[select.get("name")] = select.xpath("string(option[@selected]/@value)")
        return form

    def test_reset_password(self):
        token = self.partner.signup_token
        # Fetch reset password form
        form = self.get_form(self.test_client, "/web/reset_password", token=token)

        # Check that firstname and lastname are present and correctly valued
        self.assertEqual(self.partner.lastname, form.get("lastname", False))
        self.assertEqual(self.partner.firstname, form.get("firstname", False))
        self.assertEqual("portal", form.get("login", False))

        # Reset the password
        data = {
            "login": "portal",
            "password": "dummy_pass",
            "confirm_password": "dummy_pass",
            "csrf_token": form.get("csrf_token", False),
            "token": token,
        }
        res = self.test_client.post(
            "/web/reset_password", data=data, environ_base=self.werkzeug_environ
        )
        self.assertEqual(303, res.status_code)
        self.assertIn("/my", res.location)
        # Test authentication with the new password
        self.assertTrue(
            self.registry["res.users"].authenticate(
                get_db_name(), "portal", "dummy_pass", None
            )
        )
