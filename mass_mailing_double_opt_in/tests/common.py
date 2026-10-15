from lxml import html

from odoo import Command, http
from odoo.tests import HttpCase, TransactionCase


def _get_optin_confirm_link(mail):
    page = html.fromstring(mail.body_html)
    return page.xpath("//a[hasclass('btn-primary')]/@href")[0]


class DoubleOptInCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.mailing_list = cls.env.ref("mass_mailing.mailing_list_1")

        portal_group = cls.env.ref("base.group_portal")
        double_opt_in_group = cls.env.ref(
            "mass_mailing_double_opt_in.double_optin_user"
        )

        cls.opt_in_user = cls.env["res.users"].create(
            {
                "name": "Double Opt-in User",
                "login": "double@opt.in",
                "groups_id": [Command.set(portal_group.ids + double_opt_in_group.ids)],
            }
        )

    def _send_subscription_request(self, email, mail_list=None, user=None):
        if not mail_list:
            mail_list = self.mailing_list
        if not user:
            user = self.opt_in_user

        res = mail_list.with_user(user).request_newsletter_subscription(email)
        return res

    def assertJsonResultMessage(self, res, expected_code, expected_msg_snippet):
        self.assertEqual(expected_code, res["result"])
        self.assertIn(expected_msg_snippet, res["msg"])


class DoubleOptInControllerCommon(DoubleOptInCommon, HttpCase):
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
