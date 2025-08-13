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
    def setUp(self):
        super().setUp()
        self.test_client = Client(http.root, Response)
        self.werkzeug_environ = {
            "REMOTE_ADDR": "127.0.0.1",
            "HTTP_USER_AGENT": "user-agent",
            "HTTP_ACCEPT_LANGUAGE": "common",
        }
        self.test_client.get("/web/session/logout")

    def check_redirect(self, path, expected_path):
        resp = self.test_client.get(
            "/shop/redirect?" + path,
            follow_redirects=False,
            environ_base=self.werkzeug_environ,
        )
        self.assertEqual(resp.status_code, 302)

        self.assertEqual(urlparse(resp.headers["Location"]).path, expected_path)

    def test_shop_redirect_ok(self):
        self.check_redirect("aff_ref=1&redirect=/test/a", "/test/a")

    def test_shop_redirect_spam(self):
        self.check_redirect("redirect=https://mystupidsite.com", "/shop")


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
            result = self.pay_cart(token=token.id)

        self.assertEqual(result, "/shop/payment/validate")
        calls = mocked_act.call_args_list
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][0], ("GET", "get-mandates"))
        self.assertEqual(calls[1][0], ("POST", "create-payins"))
