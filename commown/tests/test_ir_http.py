import json
from urllib.parse import parse_qs, urlparse

from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse

from odoo.service import wsgi_server
from odoo.tests.common import HttpCase

from .common import PortalMixin


class IrHttpTC(HttpCase):
    def setUp(self):
        super().setUp()
        self.werkzeug_environ = {"REMOTE_ADDR": "127.0.0.1"}

    def test_redirect_forbiden_page(self):
        test_client = Client(wsgi_server.application, BaseResponse)
        response = test_client.get("/my")
        self.assertEqual(response.status_code, 302)
        parsed_response = urlparse(response.headers["Location"]).query
        self.assertEqual(
            parse_qs(parsed_response), {"redirect": ["http://localhost/my"]}
        )

    def test_redirect(self):
        test_client = Client(wsgi_server.application, BaseResponse)
        pt1 = self.env.ref("product.product_delivery_01_product_template")
        pt2 = self.env.ref("product.product_delivery_02_product_template")

        pt1.website_published = False

        # Check Prerequisite
        response = test_client.get(pt1.website_url, follow_redirects=False)
        self.assertEqual(response.status_code, 403)

        self.env["website.redirect"].create(
            {"type": "302", "url_from": pt1.website_url, "url_to": pt2.website_url}
        )
        response = test_client.get(pt1.website_url, follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith(pt2.website_url))


class SessionInfoTC(PortalMixin, HttpCase):
    "Test dedicated to ir_http session_info method override"

    def get_session_info(self):
        response = self.portal_client().get(
            "/web/session/get_session_info",
            content_type="application/json",
            data="{}",
            headers={"Accept": "application/json"},
        )
        return json.loads(response.data)["result"]

    def test_session_info_no_in_group_user(self):
        self.assertIs(self.get_session_info().get("is_in_group_user"), False)

    def test_session_info_in_group_user(self):
        with self.registry.cursor() as test_cursor:
            env = self.env(test_cursor)
            user = env["res.partner"].browse(self.partner.id).user_ids[0]
            env.ref("base.group_portal").users -= user
            env.ref("base.group_user").users |= user

        self.assertIs(self.get_session_info().get("is_in_group_user"), True)
