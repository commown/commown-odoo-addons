from cryptography.fernet import Fernet

from odoo import _, api, models
from odoo.tools import email_normalize


class DoubleOptInMailingList(models.Model):
    _inherit = "mailing.list"

    @api.model
    def _sudo_get_double_opt_in_encrypt_key(self):
        fernet_err_msg = _("Double opt-in subscription is not correctly set-up.")
        key = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("mass_mailing_double_opt_in.cryptographic_key")
        )
        if not key:
            raise ValueError(fernet_err_msg)

        try:
            f = Fernet(key.encode("utf-8"))
        except ValueError as exc:
            raise ValueError(fernet_err_msg) from exc

        return f

    @api.model
    def _send_newsletter_confirm_email(self, email_to, subject, msg_body):
        render_ctx = {
            "message": self.env["mail.message"].new({"body": msg_body}),
            "record_name": subject,
            "subtitles": False,
            "company": self.env.company,
        }
        rendered_body = self.env["ir.qweb"]._render(
            "mail.mail_notification_layout", render_ctx
        )

        body = self.env["mail.render.mixin"]._replace_local_links(rendered_body)

        self.env["mail.mail"].sudo().create(
            {
                "email_from": self.env.user.email,
                "email_to": email_to,
                "subject": subject,
                "body_html": body,
            }
        ).send()

    def request_newsletter_subscription(self, email):
        # Validate self
        if len(self.exists()) != 1:
            return {
                "result": "NOK",
                "msg": _("The provided mailing list does not exist."),
            }

        if not self.env.user.has_group("mass_mailing_double_opt_in.double_optin_user"):
            return {
                "result": "NOK",
                "msg": _("You do not have access to this endpoint"),
            }

        # Validate email
        email_normalized = email_normalize(email)
        if not email_normalized:
            return {
                "result": "NOK",
                "msg": _("The provided email address is invalid."),
            }

        # Checking existing contacts on the list
        existing_contacts = self.env["mailing.contact"].search_count(
            [
                ("email", "=", email_normalized),
                ("list_ids", "=", self.id),
            ]
        )
        if existing_contacts > 0:
            subject = _("Subscription already completed")
            message_body = self.env["ir.qweb"]._render(
                "mass_mailing_double_opt_in.already_subscribed_email"
            )
        else:
            # Encryption initialization
            try:
                f = self._sudo_get_double_opt_in_encrypt_key()
            except ValueError as exc:
                return {"result": "NOK", "msg": exc.args[0]}

            sign = f.encrypt(f"{email_normalized}|{self.id}".encode())

            # Render mail content
            subject = _("Confirm your newsletter subscription")
            message_body = self.env["ir.qweb"]._render(
                "mass_mailing_double_opt_in.second_opt_in_email",
                {"sign": sign},
            )

        self._send_newsletter_confirm_email(email_normalized, subject, message_body)

        return {
            "result": "OK",
            "msg": _("You will receive a mail shortly to confirm your subscription!"),
        }
