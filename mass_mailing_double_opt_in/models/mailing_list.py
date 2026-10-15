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

        sign = f"{email_normalized}|{self.id}".encode()

        # Render mail content
        message_body = self.env["ir.qweb"]._render(
            "mass_mailing_double_opt_in.second_opt_in_email",
            {"sign": sign},
        )

        # Render mail with layout
        render_ctx = {
            "message": self.env["mail.message"].new({"body": message_body}),
            "record_name": _("Confirm your newsletter subscription"),
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
                "email_to": email_normalized,
                "subject": _("Confirm your newsletter subscription"),
                "body_html": body,
            }
        ).send()

        return {
            "result": "OK",
            "msg": _("You will receive a mail shortly to confirm your subscription!"),
        }
