from cryptography.fernet import Fernet

from odoo import _, models
from odoo.tools import email_normalize


class DoubleOptInMailingList(models.Model):
    _inherit = "mailing.list"

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
            return {
                "result": "NOK",
                "msg": _("You're already subscribed to the newsletter."),
            }

        # Encryption initialization
        fernet_err_msg = _("Double opt-in subscription is not correctly set-up.")
        try:
            key = (
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("mass_mailing_double_opt_in.cryptographic_key")
            )
            if not key:
                return {"result": "NOK", "msg": fernet_err_msg}

            f = Fernet(key.encode("utf-8"))
        except ValueError:
            return {"result": "NOK", "msg": fernet_err_msg}

        sign = f.encrypt(f"{email_normalized}|{self.id}".encode())

        rendered_body = self.env["ir.qweb"]._render(
            "mass_mailing_double_opt_in.second_opt_in_email",
            {"sign": sign},
        )
        body = self.env["mail.render.mixin"]._replace_local_links(rendered_body)

        self.env["mail.mail"].sudo().create(
            {
                "email_from": self.env.user.email,
                "email_to": email_normalized,
                "subject": _("Confirm your newsletter subscription"),
                "body_html": body,
            }
        ).send()

        return {
            "result": "OK",
            "msg": _("You will receive a mail shortly to confirm your subscription!"),
        }
