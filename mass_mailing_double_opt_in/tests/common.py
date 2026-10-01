import json

from lxml import html

from odoo.tests import HttpCase


def _get_optin_confirm_link(mail):
    page = html.fromstring(mail.body_html)
    return page.xpath("//a/@href")[0]


class DoubleOptInCommon(HttpCase):
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
        )

        self.assertFalse(res.json().get("error", False))
        return res

    def assertJsonResultMessage(self, res, expected_code, expected_msg_snippet):
        res_json = res.json()["result"]

        self.assertEqual(expected_code, res_json["result"])
        self.assertEqual(expected_msg_snippet, res_json["msg"])
