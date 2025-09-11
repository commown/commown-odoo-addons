from unittest.mock import patch

from odoo.tests import TransactionCase

from odoo.addons.mail.models.mail_mail import MailMail


class CommownResUsersTC(TransactionCase):
    def test_no_reset_email_with_import(self):
        model_users = self.env["res.users"]

        # Override unlink to not delete the email if the send works (see auth_signup/tests/test_auth_signup)
        with patch.object(MailMail, "unlink", lambda self: None):
            # No import_file case: a mail should be sent.
            user_1 = model_users.create(
                {"name": "User 1", "login": "user-1", "email": "user1@test.coop"}
            )

            # import_file case : no mail should be sent
            model_users = model_users.with_context(import_file=True)
            user_2 = model_users.create(
                {"name": "User 2", "login": "user-2", "email": "user1@test.coop"}
            )

        # Fetching messages sent on res.users models
        users_mails = self.env["mail.message"].search([("model", "=", "res.users")])

        self.assertEqual(
            len(users_mails.filtered(lambda mail: mail.res_id == user_1.id)), 1
        )
        self.assertFalse(users_mails.filtered(lambda mail: mail.res_id == user_2.id))
