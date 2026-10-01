import json

from lxml import html

from odoo.tests import HttpCase

TIMEOUT = 10000  # for debugging purposes


class MassMailingDoubleOptInTC(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.mailing_list = cls.env.ref("mass_mailing.mailing_list_1")

    def _send_subscription_request(self, email, mail_list_id=None):
        if not mail_list_id:
            mail_list_id = self.mailing_list.id

        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "email": email,
                "list_id": mail_list_id,
            },
        }

        res = self.url_open(
            "/newsletter/request_subscription",
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload),
            timeout=TIMEOUT,
        )

        self.assertFalse(res.json().get("error", False))
        return res

    def _get_optin_confirm_link(self, mail):
        page = html.fromstring(mail.body_html)
        return page.xpath("//a/@href")[0]

    def test_double_opt_in_subscription_ok(self):
        "Following a double opt-in subscription from start to finish"
        email = "dummy@mail.com"

        # First opt-in
        req_res = self._send_subscription_request(email)

        json_res = req_res.json()["result"]
        self.assertEqual("OK", json_res["result"])
        self.assertIn("will receive a mail shortly", json_res["msg"])

        confirm_mail = self.env["mail.mail"].search([("email_to", "=", email)])
        self.assertTrue(confirm_mail)

        confirm_link = self._get_optin_confirm_link(confirm_mail)
        self.assertIn("/newsletter/confirm_subscription", confirm_link)

    def test_subscription_request_nok_invalid_email(self):
        res = self._send_subscription_request("invalid")

        json_res = res.json()["result"]
        self.assertEqual("NOK", json_res["result"])
        self.assertIn("email address is invalid", json_res["msg"])

    def test_subscription_request_nok_invalid_list(self):
        res = self._send_subscription_request("dummy@mail.com", mail_list_id=-1)

        json_res = res.json()["result"]
        self.assertEqual("NOK", json_res["result"])
        self.assertIn("list does not exist", json_res["msg"])

    def test_subscription_request_nok_already_subscribed(self):
        email = "dummy@mail.com"
        self.env["mailing.contact"].sudo().with_context(
            default_list_ids=self.mailing_list.ids
        ).create({"email": email})

        res = self._send_subscription_request(email)

        json_res = res.json()["result"]
        self.assertEqual("NOK", json_res["result"])
        self.assertIn("already subscribed", json_res["msg"])
