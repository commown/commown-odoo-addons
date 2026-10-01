from .common import DoubleOptInCommon, _get_optin_confirm_link


class DoubleOptInTC(DoubleOptInCommon):
    def test_double_opt_in_subscription_ok(self):
        "Following a double opt-in subscription from start to finish"
        email = "dummy@mail.com"

        # First opt-in
        req_res = self._send_subscription_request(email)
        self.assertJsonResultMessage(req_res, "OK", "will receive a mail")

        confirm_mail = self.env["mail.mail"].search([("email_to", "=", email)])
        self.assertTrue(confirm_mail)

        confirm_link = _get_optin_confirm_link(confirm_mail)
        self.assertIn("/newsletter/confirm_subscription", confirm_link)

    def test_subscription_request_nok_invalid_email(self):
        res = self._send_subscription_request("invalid")
        self.assertJsonResultMessage(res, "NOK", "email address is invalid")

    def test_subscription_request_nok_invalid_list(self):
        res = self._send_subscription_request("dummy@mail.com", mail_list_id=-1)
        self.assertJsonResultMessage(res, "NOK", "list does not exist")

    def test_subscription_request_nok_already_subscribed(self):
        email = "dummy@mail.com"
        self.env["mailing.contact"].sudo().with_context(
            default_list_ids=self.mailing_list.ids
        ).create({"email": email})

        res = self._send_subscription_request(email)
        self.assertJsonResultMessage(res, "NOK", "already subscribed")
