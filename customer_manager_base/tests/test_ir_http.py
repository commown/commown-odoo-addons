import json

from lxml import html
from werkzeug.test import Client
from werkzeug.wrappers import Response

from odoo import http
from odoo.tests.common import HttpCase, get_db_name


class SessionInfoTC(HttpCase):
    "Test dedicated to ir_http session_info method override"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env.ref("base.partner_demo_portal")
        cls.partner.signup_prepare()
        cls.env.cr.savepoint()
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
        form = {n.get("name"): n.get("value") for n in page.xpath("//input")}
        for select in page.xpath("//select"):
            form[select.get("name")] = select.xpath("string(option[@selected]/@value)")
        return form

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

    def get_session_info(self):
        response = self.portal_client().get(
            "/web/session/get_session_info",
            content_type="application/json",
            data="{}",
            headers={"Accept": "application/json"},
        )
        return json.loads(response.data)["result"]

    def test_session_info_is_customer_admin_false(self):
        with self.registry.cursor() as test_cursor:
            env = self.env(test_cursor)
            partner = env["res.partner"].browse(self.partner.id)
            # Check test prerequisite
            self.assertFalse(partner.parent_id)

        self.assertIs(self.get_session_info().get("is_customer_admin"), False)

    def test_session_info_is_customer_admin_true(self):
        with self.registry.cursor() as test_cursor:
            env = self.env(test_cursor)
            partner = env["res.partner"].browse(self.partner.id)
            partner.user_ids.groups_id |= env.ref(
                "customer_manager_base.group_customer_admin"
            )

        self.assertIs(self.get_session_info().get("is_customer_admin"), True)
