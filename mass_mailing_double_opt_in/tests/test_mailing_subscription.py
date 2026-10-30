from . import common


class DoubleOptInTC(common.DoubleOptInCommon):
    def test_subscription_request_ok(self):
        email = "dummy@mail.com"

        # First opt-in
        req_res = self._send_subscription_request(email)
        self.assertJsonResultMessage(req_res, "OK", "will receive a mail")

        confirm_mail = self.env["mail.mail"].search([("email_to", "=", email)])
        self.assertTrue(confirm_mail)

        confirm_link = common._get_optin_confirm_link(confirm_mail)
        self.assertIn("/newsletter/confirm_subscription", confirm_link)

    def test_subscription_request_nok_invalid_email(self):
        res = self._send_subscription_request("invalid")
        self.assertJsonResultMessage(res, "NOK", "email address is invalid")

    def test_subscription_request_nok_invalid_list(self):
        invalid_mail_list = self.env["mailing.list"].browse(-1)
        res = self._send_subscription_request(
            "dummy@mail.com", mail_list=invalid_mail_list
        )
        self.assertJsonResultMessage(res, "NOK", "list does not exist")

    def test_subscription_request_nok_already_subscribed(self):
        email = "dummy@mail.com"
        self.env["mailing.contact"].sudo().with_context(
            default_list_ids=self.mailing_list.ids
        ).create({"email": email})

        res = self._send_subscription_request(email)
        self.assertJsonResultMessage(res, "NOK", "already subscribed")

    def test_subscription_request_nok_invalid_opt_in_user(self):
        "Only the dedicated opt-in user can perform a subscription request"
        admin_user = self.env.ref("base.user_admin")
        res = self._send_subscription_request("dummy@mail.com", user=admin_user)

        self.assertJsonResultMessage(res, "NOK", "not have access to this endpoint")


class DoubleOptInControllerTC(common.DoubleOptInControllerCommon):
    def _get_subscriptions_for_list(self, email, list_id=None):
        if not list_id:
            list_id = self.mailing_list.id

        return self.env["mailing.contact.subscription"].search(
            [
                ("contact_id.email", "=", email),
                ("list_id", "=", self.mailing_list.id),
            ]
        )

    def test_double_opt_in_subscription_ok(self):
        "Following a double opt-in subscription from start to finish"
        email = "dummy@mail.com"

        # First opt-in
        req_res = self._send_subscription_request(email)
        self.assertJsonResultMessage(req_res, "OK", "will receive a mail")

        confirm_mail = self.env["mail.mail"].search([("email_to", "=", email)])
        self.assertTrue(confirm_mail)

        confirm_link = common._get_optin_confirm_link(confirm_mail)
        self.assertIn("/newsletter/confirm_subscription", confirm_link)

        confirm_res = self._open_confirmation_request(confirm_link)
        self.assertConfirmPageTitle(
            confirm_res, "Your subscription has been completed!"
        )

        subscription = self._get_subscriptions_for_list(email)
        self.assertTrue(subscription)

    def _generate_confirm_link(self, email, list_id=None):
        "Utility to bypass the request procedure"
        if not list_id:
            list_id = self.mailing_list.id

        sign = f"{email}|{list_id}"
        return f"/newsletter/confirm_subscription?sign={sign}"

    def test_subscription_confirmation_nok_already_confirmed(self):
        email = "test@test.coop"
        confirm_link = self._generate_confirm_link(email)

        confirm_res_1 = self._open_confirmation_request(confirm_link)
        self.assertConfirmPageTitle(
            confirm_res_1, "Your subscription has been completed!"
        )
        self.assertEqual(1, len(self._get_subscriptions_for_list(email)))

        # Trying to confirm the subscription again
        confirm_res_2 = self._open_confirmation_request(confirm_link)
        self.assertConfirmPageTitle(confirm_res_2, "Subscription already completed")

        self.assertEqual(1, len(self._get_subscriptions_for_list(email)))

    def test_subscription_confirmation_nok_invalid_token(self):
        res = self._open_confirmation_request(
            "/newsletter/confirm_subscription?sign=dummy"
        )

        self.assertConfirmPageTitle(res, "Your subscription has failed...")
        self.assertIn("values were invalid", res.text)
