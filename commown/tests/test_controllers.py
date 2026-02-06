import os
from unittest.mock import patch
from urllib.parse import urlparse

from werkzeug.test import Client
from werkzeug.wrappers import Response

from odoo import http
from odoo.tests import HttpCase, tagged

from odoo.addons.account_payment_slimpay.models.slimpay_utils import SlimpayClient
from odoo.addons.server_environment import server_env
from odoo.addons.server_environment.models import server_env_mixin
from odoo.addons.website_sale_payment_slimpay.tests.common import SlimpayControllersTC


@tagged("-at_install", "post_install")
class ControllerTC(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_client = Client(http.root, Response)
        cls.werkzeug_environ = {
            "REMOTE_ADDR": "127.0.0.1",
            "HTTP_USER_AGENT": "user-agent",
            "HTTP_ACCEPT_LANGUAGE": "common",
        }
        cls.test_client.get("/web/session/logout")

    def check_redirect(self, path, expected_path, expected_netloc="localhost"):
        resp = self.test_client.get(
            "/shop/redirect?" + path,
            follow_redirects=False,
            environ_base=self.werkzeug_environ,
        )
        self.assertEqual(resp.status_code, 303)

        url = urlparse(resp.headers["Location"])
        self.assertEqual(url.path, expected_path)
        self.assertEqual(url.netloc, expected_netloc)

    def test_shop_redirect_local(self):
        "Links leading to locations on the same website should redirect correctly"
        self.check_redirect("aff_ref=1&redirect=/test/a", "/test/a")

    def test_shop_redirect_external(self):
        "Links leading to commown.coop links should redirect correctly"
        # Setup
        param = self.env.ref("commown.allowed_redirect_netlocs")
        param.value = "commown.coop"
        param.invalidate_recordset()

        # Case 1: Trying to redirect to an allowed site
        self.check_redirect(
            "redirect=https://commown.coop/", "/", expected_netloc="commown.coop"
        )

    def test_shop_redirect_spam(self):
        "Links leading to unallowed third-party sites should redirect to the Odoo shop"
        self.check_redirect("redirect=https://mystupidsite.com", "/shop")

    def test_shop_redirect_odoo_app_location(self):
        "Links leading to the Odoo website app locations should redirect correctly"
        website = self.env.ref("website.default_website")
        website.domain = "https://website.com/"
        website.invalidate_recordset()

        self.check_redirect(
            "redirect=https://website.com/", "/", expected_netloc="website.com"
        )


class TestSlimpayPaymentControllerTC(SlimpayControllersTC):
    def setUp(self):
        os.environ.update(
            {
                "SERVER_ENV_CONFIG": (
                    "[payment_provider.Slimpay]\n"
                    "slimpay_api_url=https://api.preprod.slimpay.com\n"
                    "slimpay_creditor=democreditor\n"
                    "slimpay_app_id=democreditor01\n"
                    "slimpay_app_secret=democreditor01"
                ),
            }
        )
        parser = server_env._load_config()
        server_env_mixin.serv_config = parser
        super().setUp()

    def test_slimpay_portal_sale_ok_with_token(self):
        ref = self.env.ref
        partner = ref("base.partner_demo_portal")
        provider = ref("account_payment_slimpay.payment_provider_slimpay")

        token = self.env["payment.token"].create(
            {
                "payment_details": "Test token",
                "partner_id": partner.id,
                "provider_id": provider.id,
                "provider_ref": "test slimpay ref",
            }
        )
        partner.payment_token_id = token.id

        self.authenticate("portal", "portal")
        self.add_product_to_user_cart()

        def action_mock(action, short_method_name, *args, **kwargs):
            return {
                ("GET", "get-mandates"): {"reference": "test mandate ref"},
                ("POST", "create-payins"): {
                    "executionStatus": "toprocess",
                    "state": "accepted",
                    "reference": "payment reference",
                },
            }[(action, short_method_name)]

        with patch.object(
            SlimpayClient, "action", side_effect=action_mock
        ) as mocked_act:
            self.pay_cart(token=token.id)

        calls = mocked_act.call_args_list
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][0], ("GET", "get-mandates"))
        self.assertEqual(calls[1][0], ("POST", "create-payins"))
