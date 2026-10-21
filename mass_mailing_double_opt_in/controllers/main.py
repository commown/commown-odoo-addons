from cryptography.fernet import InvalidToken

from odoo import _, http
from odoo.http import Controller, request


class DoubleOptInController(Controller):
    @http.route(
        "/newsletter/confirm_subscription", type="http", auth="public", website="True"
    )
    def confirm_newsletter_subscription(self, sign=""):
        env = request.env
        res_tmpl_id = "mass_mailing_double_opt_in.confirm"

        # Encryption initialization
        try:
            f = env["mailing.list"]._sudo_get_double_opt_in_encrypt_key()
        except ValueError as exc:
            return request.render(res_tmpl_id, {"err_msg": exc.args[0]})

        # Signature validation
        try:
            sign = f.decrypt(sign.encode("utf-8")).decode("utf-8")
            email, list_id = sign.split("|")

            # Fetch mailing list, raising a Value Error if invalid
            list_id = int(list_id)
            mail_list = env["mailing.list"].browse(list_id).exists().ensure_one()
        except (ValueError, InvalidToken):
            values_err_msg = _("The provided confirmation values were invalid.")
            return request.render(res_tmpl_id, {"err_msg": values_err_msg})

        ContactSudo = env["mailing.contact"].sudo()

        # Checking if the email is already subscribed
        existing_contacts = ContactSudo.search_count(
            [
                ("email", "=", email),
                ("list_ids", "=", list_id),
            ],
        )
        if existing_contacts:
            render_ctx = {"already_subscribed": True, "email": email}
            return request.render(res_tmpl_id, render_ctx)

        # Creating the mailing contact
        ContactSudo.with_context(default_list_ids=mail_list.ids).create(
            {"email": email, "ip_addr": request.httprequest.remote_addr}
        )

        return request.render(res_tmpl_id, {"email": email})
