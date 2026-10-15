import json

from lxml import html

from odoo import Command, http
from odoo.tests import HttpCase


def _get_optin_confirm_link(mail):
    page = html.fromstring(mail.body_html)
    return page.xpath("//a/@href")[0]


class DoubleOptInCommon(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.mailing_list = cls.env.ref("mass_mailing.mailing_list_1")

        portal_group = cls.env.ref("base.group_portal")
        double_opt_in_group = cls.env.ref(
            "mass_mailing_double_opt_in.double_optin_user"
        )

        cls.password = "dummy_password"

        cls.opt_in_user = cls.env["res.users"].create(
            {
                "name": "Double Opt-in User",
                "login": "double@opt.in",
                "password": cls.password,
                "groups_id": [Command.set(portal_group.ids + double_opt_in_group.ids)],
            }
        )

    def _send_subscription_request(
        self, email, mail_list_id=None, login=None, password=None
    ):
        if not mail_list_id:
            mail_list_id = self.mailing_list.id
        if not login:
            login = self.opt_in_user.login
        if not password:
            password = self.password

        self.authenticate(login, password)

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
        self.logout()

        self.assertFalse(res.json().get("error", False))
        return res

    def assertJsonResultMessage(self, res, expected_code, expected_msg_snippet):
        res_json = res.json()["result"]

        self.assertEqual(expected_code, res_json["result"])
        self.assertIn(expected_msg_snippet, res_json["msg"])

    def _open_confirmation_request(self, link):
        # This is used to display the debug error in the rendered page.
        self.authenticate(None, None)
        self.session.debug = "1"
        http.root.session_store.save(self.session)

        res = self.url_open(link)
        res.raise_for_status()

        return res

    def assertConfirmPageTitle(self, res, title):
        page = html.fromstring(res.text)
        self.assertIn(title, "".join(page.xpath("//h2/text()")))
