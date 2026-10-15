import json

from cryptography.fernet import Fernet
from lxml import html

from odoo import Command, http
from odoo.tests import HttpCase

TIMEOUT = 10000  # for debugging purposes


class MassMailingDoubleOptInTC(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.mailing_list = cls.env.ref("mass_mailing.mailing_list_1")

        key = Fernet.generate_key()
        cls.env["ir.config_parameter"].set_param(
            "mass_mailing_double_opt_in.cryptographic_key",
            key.decode("utf-8"),
        )

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
            timeout=TIMEOUT,
        )
        self.logout()

        self.assertFalse(res.json().get("error", False))
        return res

    def _get_optin_confirm_link(self, mail):
        page = html.fromstring(mail.body_html)
        return page.xpath("//a/@href")[0]

    def _open_confirmation_request(self, link):
        # This is used to display the debug error in the rendered page.
        session = self.authenticate(None, None)
        session.debug = "1"
        http.root.session_store.save(self.session)

        res = self.url_open(link)
        res.raise_for_status()

        return res

    def assertConfirmPageTitle(self, res, title):
        page = html.fromstring(res.text)
        self.assertIn(title, "".join(page.xpath("//h2/text()")))

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

        confirm_res = self._open_confirmation_request(confirm_link)
        self.assertConfirmPageTitle(
            confirm_res, "Your subscription has been completed!"
        )

        subscription = self.env["mailing.contact.subscription"].search(
            [
                ("contact_id.email", "=", email),
                ("list_id", "=", self.mailing_list.id),
            ]
        )
        self.assertTrue(subscription)

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

    def test_subscription_request_nok_invalid_opt_in_user(self):
        "Only the dedicated opt-in user can perform a subscription request"
        res = self._send_subscription_request(
            "dummy@mail.com", login="admin", password="admin"
        )
        json_res = res.json()["result"]

        self.assertEqual("NOK", json_res["result"])
        self.assertIn("not have access to this endpoint", json_res["msg"])

    def test_subscription_confirmation_nok_invalid_token(self):
        res = self._open_confirmation_request(
            "/newsletter/confirm_subscription?sign=dummy"
        )

        self.assertConfirmPageTitle(res, "Your subscription has failed...")
        self.assertIn("values were invalid", res.text)

    def test_encryption_key_disabled(self):
        self.env["ir.config_parameter"].search(
            [("key", "=", "mass_mailing_double_opt_in.cryptographic_key")]
        ).unlink()

        request_res = self._send_subscription_request("dummy@mail.com")
        json_res = request_res.json()["result"]
        self.assertEqual("NOK", json_res["result"])
        self.assertIn("is not correctly set-up", json_res["msg"])

        confirm_res = self._open_confirmation_request(
            "/newsletter/confirm_subscription?sign=dummy"
        )

        self.assertConfirmPageTitle(confirm_res, "Your subscription has failed...")
        self.assertIn("not correctly set-up", confirm_res.text)
