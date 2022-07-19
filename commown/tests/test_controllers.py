from urllib.parse import urlparse

from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse

from odoo.service import wsgi_server

from odoo.tests.common import HttpCase, at_install, post_install


@at_install(False)
@post_install(True)
class ControllerTC(HttpCase):
    def setUp(self):
        super().setUp()
        self.test_client = Client(wsgi_server.application, BaseResponse)
        self.test_client.get("/web/session/logout")

    def check_redirect(self, path, expected_path):
        resp = self.test_client.get("/shop/redirect?" + path, follow_redirects=False)

        self.assertEqual(resp.status_code, 302)

        self.assertEqual(urlparse(resp.headers["Location"]).path, expected_path)

    def test_shop_redirect_ok(self):
        self.check_redirect("aff_ref=1&redirect=/test/a", "/test/a")

    def test_shop_redirect_spam(self):
        self.check_redirect("redirect=https://mystupidsite.com", "/shop")
