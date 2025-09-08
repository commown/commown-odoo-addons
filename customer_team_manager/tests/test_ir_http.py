import json

from lxml import html
from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse

from odoo.service import wsgi_server
from odoo.tests.common import HttpCase, get_db_name


class SessionInfoTC(HttpCase):
    "Test dedicated to ir_http session_info method override"

    def setUp(self):
        super().setUp()
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

    def portal_client(self, user, password="portal"):
        test_client = Client(wsgi_server.application, BaseResponse)

        login_form = self.get_form(test_client, "/web/login/", db=get_db_name())
        login_form.update(
            {
                "login": user.login,
                "password": password,
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

    def get_session_info(self, user, password="portal"):
        response = self.portal_client(user, password).get(
            "/web/session/get_session_info",
            content_type="application/json",
            data="{}",
            headers={"Accept": "application/json"},
        )
        return json.loads(response.data)["result"]

    def test_session_info_is_customer_false(self):
        user = self.env.ref("base.user_demo")
        user.password = "portal"

        self.assertFalse(self.get_session_info(user).get("is_customer"))

    def test_session_info_is_customer_true(self):
        partner = self.env.ref("base.partner_demo_portal")
        user = partner.user_ids.ensure_one()

        self.assertTrue(self.get_session_info(user).get("is_customer"))
