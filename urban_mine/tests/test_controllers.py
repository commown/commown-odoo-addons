import json

from odoo.tests.common import TransactionCase

from odoo.addons.website.tools import MockRequest

from ..controllers.form import UrbanMineWebsiteForm


class TestUrbanMineController(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.hcaptcha_success_key = "10000000-aaaa-bbbb-cccc-000000000001"
        cls.website = cls.env.ref("website.default_website")
        cls.partner_data = {
            "model_name": "res.partner",
            "firstname": "Foo",
            "lastname": "Bar",
        }

    def test_hcaptcha_ok(self):
        "With a correct hCaptcha token, the request should succeed"
        self.partner_data.update({"h-captcha-response": self.hcaptcha_success_key})

        with MockRequest(env=self.env, website=self.website) as req:
            req.params = self.partner_data
            resp_ok = UrbanMineWebsiteForm().website_form("res.partner")

        resp_ok_data = json.loads(resp_ok.data)

        # No error message should be returned
        self.assertNotIn("error", resp_ok_data)

        # A partner should be created and its id returned with the response.
        self.assertIn("id", resp_ok_data)
        self.assertTrue(self.env["res.partner"].browse(resp_ok_data["id"]).exists())

    def test_hcaptcha_failed(self):
        """
        With a hCaptcha validation fail, the request should return an error
        (here, no token was passed, as if the user didn't check the Captcha)
        """
        with MockRequest(env=self.env, website=self.website) as req:
            req.params = self.partner_data
            resp_no_token = UrbanMineWebsiteForm().website_form("res.partner")

        resp_no_token_data = json.loads(resp_no_token.data)

        # No partner should be created. (ie. no return id)
        self.assertNotIn("id", resp_no_token_data)

        # An error message should be returned.
        self.assertTrue("error", resp_no_token_data)
        self.assertIn("Captcha failed", resp_no_token_data["error"])
