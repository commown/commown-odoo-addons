from cryptography.fernet import Fernet, InvalidToken

from odoo import _, http
from odoo.http import Controller, request
from odoo.tools import email_normalize


class MassMailingDoubleOptInController(Controller):
    @http.route("/newsletter/request_subscription", type="json", auth="user")
    def request_newsletter_subscription(self, email, list_id):
        env = request.env

        if not env.user.has_group("mass_mailing_double_opt_in.double_optin_user"):
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

        # Validate list_id
        mailing_list = env["mailing.list"].browse(list_id).exists()
        if not mailing_list:
            return {
                "result": "NOK",
                "msg": _("The provided mailing list does not exist."),
            }

        existing_contacts = env["mailing.contact"].search_count(
            [
                ("email", "=", email_normalized),
                ("list_ids", "=", mailing_list.id),
            ]
        )
        if existing_contacts > 0:
            return {
                "result": "NOK",
                "msg": _("You're already subscribed to the newsletter."),
            }
        key = (
            env["ir.config_parameter"]
            .sudo()
            .get_param("mass_mailing_double_opt_in.cryptographic_key")
        )
        if not key:
            return {
                "result": "NOK",
                "msg": _("Double opt-in subscription is not correctly set-up."),
            }

        f = Fernet(key.encode("utf-8"))

        sign = f.encrypt(f"{email_normalized}|{list_id}".encode())

        rendered_body = env["ir.qweb"]._render(
            "mass_mailing_double_opt_in.second_opt_in_email",
            {"sign": sign},
        )
        body = env["mail.render.mixin"]._replace_local_links(rendered_body)

        env["mail.mail"].sudo().create(
            {
                "email_from": env.user.email,
                "email_to": email_normalized,
                "subject": _("Confirm your newsletter subscription"),
                "body_html": body,
            }
        ).send()

        return {
            "result": "OK",
            "msg": _("You will receive a mail shortly to confirm your subscription!"),
        }

    @http.route(
        "/newsletter/confirm_subscription", type="http", auth="public", website="True"
    )
    def confirm_newsletter_subscription(self, sign=""):
        env = request.env
        err_msg = _("The provided confirmation values were invalid.")

        key = (
            env["ir.config_parameter"]
            .sudo()
            .get_param("mass_mailing_double_opt_in.cryptographic_key")
        )
        if not key:
            values = {
                "err_msg": _("Double opt-in subscription is not correctly set-up.")
            }
            return request.render("mass_mailing_double_opt_in.confirm", values)
        f = Fernet(key.encode("utf-8"))

        try:
            sign = f.decrypt(sign.encode("utf-8")).decode("utf-8")
            email, list_id = sign.split("|")

            # Fetch mailing list, raising a Value Error if invalid
            list_id = int(list_id)
            mail_list = env["mailing.list"].browse(list_id).exists().ensure_one()
        except (ValueError, InvalidToken):
            values = {"err_msg": err_msg}
            return request.render("mass_mailing_double_opt_in.confirm", values)

        env["mailing.contact"].sudo().with_context(
            default_list_ids=mail_list.ids
        ).create({"email": email})

        values = {"email": email}
        return request.render("mass_mailing_double_opt_in.confirm", values)
