from lxml import html

from odoo.tests import TransactionCase


def _get_optin_confirm_link(mail):
    page = html.fromstring(mail.body_html)
    return page.xpath("//a[hasclass('btn-primary')]/@href")[0]


class DoubleOptInCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.mailing_list = cls.env.ref("mass_mailing.mailing_list_1")

    def _send_subscription_request(self, email, mail_list=None):
        if not mail_list:
            mail_list = self.mailing_list

        res = mail_list.request_newsletter_subscription(email)
        return res

    def assertJsonResultMessage(self, res, expected_code, expected_msg_snippet):
        self.assertEqual(expected_code, res["result"])
        self.assertIn(expected_msg_snippet, res["msg"])
